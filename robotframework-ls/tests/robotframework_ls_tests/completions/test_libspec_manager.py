import os
from pathlib import Path


def test_libspec_info(libspec_manager, tmpdir):
    from robotframework_ls.impl.robot_specbuilder import LibraryDoc
    from robotframework_ls.impl.robot_specbuilder import KeywordDoc

    assert "BuiltIn" in libspec_manager.get_library_names()
    lib_info = libspec_manager.get_library_info("BuiltIn", create=False)
    assert isinstance(lib_info, LibraryDoc)
    assert lib_info.source is not None
    assert lib_info.source.endswith("BuiltIn.py")
    for keyword in lib_info.keywords:
        assert isinstance(keyword, KeywordDoc)
        assert keyword.lineno > 0


def arg_to_dict(arg):
    return {
        "arg_name": arg.arg_name,
        "is_keyword_arg": arg.is_keyword_arg,
        "is_star_arg": arg.is_star_arg,
        "arg_type": arg.arg_type,
        "default_value": arg.default_value,
    }


def keyword_to_dict(keyword):
    from robotframework_ls.impl.robot_specbuilder import docs_and_format

    keyword = keyword
    return {
        "name": keyword.name,
        "args": [arg_to_dict(arg) for arg in keyword.args],
        "doc": keyword.doc,
        "lineno": keyword.lineno,
        "tags": keyword.tags,
        "docs_and_format": docs_and_format(keyword),
    }


def test_libspec(libspec_manager, workspace_dir, data_regression):
    from robotframework_ls.impl.robot_specbuilder import LibraryDoc
    from robotframework_ls.impl.robot_specbuilder import KeywordDoc
    from typing import List

    os.makedirs(workspace_dir)
    libspec_manager.add_additional_pythonpath_folder(workspace_dir)
    path = Path(workspace_dir) / "check_lib.py"
    path.write_text(
        """
def method(a:int=10):
    '''
    :param a: This is the parameter a.
    '''

def method2(a:int):
    pass

def method3(a=10):
    pass
    
def method4(a=10, *args, **kwargs):
    pass
    
def method5(a, *args, **kwargs):
    pass
    
def method6():
    pass
"""
    )

    library_info: LibraryDoc = libspec_manager.get_library_info("check_lib")
    keywords: List[KeywordDoc] = library_info.keywords
    data_regression.check([keyword_to_dict(k) for k in keywords])
    assert (
        int(library_info.specversion) <= 2
    ), "Libpsec version changed. Check parsing. "


def test_libspec_manager_caches(libspec_manager, workspace_dir):
    from robocorp_ls_core import uris
    import os.path
    from robotframework_ls_tests.fixtures import LIBSPEC_1
    from robotframework_ls_tests.fixtures import LIBSPEC_2
    from robotframework_ls_tests.fixtures import LIBSPEC_2_A
    import time
    from robocorp_ls_core.unittest_tools.fixtures import wait_for_test_condition

    workspace_dir_a = os.path.join(workspace_dir, "workspace_dir_a")
    os.makedirs(workspace_dir_a)
    with open(os.path.join(workspace_dir_a, "my.libspec"), "w") as stream:
        stream.write(LIBSPEC_1)
    libspec_manager.add_workspace_folder(uris.from_fs_path(workspace_dir_a))
    assert libspec_manager.get_library_info("case1_library", create=False) is not None

    libspec_manager.remove_workspace_folder(uris.from_fs_path(workspace_dir_a))
    library_info = libspec_manager.get_library_info("case1_library", create=False)
    if library_info is not None:
        raise AssertionError(
            "Expected: %s to be None after removing %s"
            % (library_info, uris.from_fs_path(workspace_dir_a))
        )

    libspec_manager.add_workspace_folder(uris.from_fs_path(workspace_dir_a))
    assert libspec_manager.get_library_info("case1_library", create=False) is not None

    # Give a timeout so that the next write will have at least 1 second
    # difference (1s is the minimum for poll to work).
    time.sleep(1.1)
    with open(os.path.join(workspace_dir_a, "my2.libspec"), "w") as stream:
        stream.write(LIBSPEC_2)

    def check_spec_found():
        library_info = libspec_manager.get_library_info("case2_library", create=False)
        return library_info is not None

    # Updating is done in a thread.
    wait_for_test_condition(check_spec_found, sleep=1 / 5.0)

    library_info = libspec_manager.get_library_info("case2_library", create=False)
    assert set(x.name for x in library_info.keywords) == set(
        ["Case 2 Verify Another Model", "Case 2 Verify Model"]
    )

    # Give a timeout so that the next write will have at least 1 second
    # difference (1s is the minimum for poll to work).
    time.sleep(1)
    with open(os.path.join(workspace_dir_a, "my2.libspec"), "w") as stream:
        stream.write(LIBSPEC_2_A)

    def check_spec_2_a():
        library_info = libspec_manager.get_library_info("case2_library", create=False)
        if library_info:
            return set(x.name for x in library_info.keywords) == set(
                ["Case 2 A Verify Another Model", "Case 2 A Verify Model"]
            )

    # Updating is done in a thread.
    wait_for_test_condition(check_spec_2_a, sleep=1 / 5.0)
