#  fixtures: Fixtures with cleanups for testing and convenience.
#
# Copyright (c) 2010, 2012  Robert Collins <robertc@robertcollins.net>
# 
# Licensed under either the Apache License, Version 2.0 or the BSD 3-clause
# license at the users choice. A copy of both licenses are available in the
# project source as Apache-2.0 and BSD. You may not use this file except in
# compliance with one of these two licences.
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under these licenses is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
# license you chose for the specific language governing permissions and
# limitations under that license.

import os
import tempfile

import testtools
from testtools.matchers import (
    DirContains,
    DirExists,
    FileContains,
    StartsWith,
    )

from fixtures import (
    NestedTempfile,
    TempDir,
    )
from fixtures._fixtures.tempdir import (
    create_normal_shape,
    normalize_entry,
    normalize_shape,
    )
from fixtures.tests.helpers import HasNoAttribute


class TestTempDir(testtools.TestCase):

    def test_basic(self):
        fixture = TempDir()
        self.assertThat(fixture, HasNoAttribute('path'))
        fixture.setUp()
        try:
            path = fixture.path
            self.assertTrue(os.path.isdir(path))
        finally:
            fixture.cleanUp()
            self.assertFalse(os.path.isdir(path))

    def test_under_dir(self):
        root = self.useFixture(TempDir()).path
        fixture = TempDir(root)
        fixture.setUp()
        with fixture:
            self.assertThat(fixture.path, StartsWith(root))


class NestedTempfileTest(testtools.TestCase):
    """Tests for `NestedTempfile`."""

    def test_normal(self):
        # The temp directory is removed when the context is exited.
        starting_tempdir = tempfile.gettempdir()
        with NestedTempfile():
            self.assertEqual(tempfile.tempdir, tempfile.gettempdir())
            self.assertNotEqual(starting_tempdir, tempfile.tempdir)
            self.assertTrue(os.path.isdir(tempfile.tempdir))
            nested_tempdir = tempfile.tempdir
        self.assertEqual(tempfile.tempdir, tempfile.gettempdir())
        self.assertEqual(starting_tempdir, tempfile.tempdir)
        self.assertFalse(os.path.isdir(nested_tempdir))

    def test_exception(self):
        # The temp directory is removed when the context is exited, even if
        # the code running in context raises an exception.
        class ContrivedException(Exception):
            pass
        try:
            with NestedTempfile():
                nested_tempdir = tempfile.tempdir
                raise ContrivedException
        except ContrivedException:
            self.assertFalse(os.path.isdir(nested_tempdir))


class TestFileTree(testtools.TestCase):

    def test_out_of_order(self):
        # If a file or a subdirectory is listed before its parent directory,
        # that doesn't matter.  We'll create the directory first.
        fixture = TempDir()
        with fixture:
            fixture.make_tree('a/b/', 'a/')
            path = fixture.path
            self.assertThat(path, DirContains(['a']))
            self.assertThat(os.path.join(path, 'a'), DirContains(['b']))
            self.assertThat(os.path.join(path, 'a', 'b'), DirExists())

    def test_not_even_creating_parents(self):
        fixture = TempDir()
        with fixture:
            fixture.make_tree('a/b/foo.txt', 'c/d/e/')
            path = fixture.path
            self.assertThat(
                os.path.join(path, 'a', 'b', 'foo.txt'),
                FileContains("The file 'a/b/foo.txt'."))
            self.assertThat(os.path.join(path, 'c', 'd', 'e'), DirExists())


class TestNormalizeEntry(testtools.TestCase):

    def test_file_as_tuple(self):
        # A tuple of filenames and contents is already normalized.
        entry = normalize_entry(('foo', 'foo contents'))
        self.assertEqual(('foo', 'foo contents'), entry)

    def test_directories_as_tuples(self):
        # A tuple of directory name and None is already normalized.
        directory = normalize_entry(('foo/', None))
        self.assertEqual(('foo/', None), directory)

    def test_directories_as_singletons(self):
        # A singleton tuple of directory name is normalized to a 2-tuple of
        # the directory name and None.
        directory = normalize_entry(('foo/',))
        self.assertEqual(('foo/', None), directory)

    def test_directories_as_strings(self):
        # If directories are just given as strings, then they are normalized
        # to tuples of directory names and None.
        directory = normalize_entry('foo/')
        self.assertEqual(('foo/', None), directory)

    def test_directories_with_content(self):
        # If we're given a directory with content, we raise an error, since
        # it's ambiguous and we don't want to guess.
        bad_entry = ('dir/', "stuff")
        e = self.assertRaises(ValueError, normalize_entry, bad_entry)
        self.assertEqual(
            "Directories must end with '/' and have no content, files do not "
            "end with '/' and must have content, got %r" % (bad_entry,),
            str(e))

    def test_filenames_as_strings(self):
        # If file names are just given as strings, then they are normalized to
        # tuples of filenames and made-up contents.
        entry = normalize_entry('foo')
        self.assertEqual(('foo', "The file 'foo'."), entry)

    def test_filenames_as_singletons(self):
        # A singleton tuple of a filename is normalized to a 2-tuple of
        # the file name and made-up contents.
        entry = normalize_entry(('foo',))
        self.assertEqual(('foo', "The file 'foo'."), entry)

    def test_filenames_without_content(self):
        # If we're given a filename without content, we raise an error, since
        # it's ambiguous and we don't want to guess.
        bad_entry = ('filename', None)
        e = self.assertRaises(ValueError, normalize_entry, bad_entry)
        self.assertEqual(
            "Directories must end with '/' and have no content, files do not "
            "end with '/' and must have content, got %r" % (bad_entry,),
            str(e))

    def test_too_long_tuple(self):
        bad_entry = ('foo', 'bar', 'baz')
        e = self.assertRaises(ValueError, normalize_entry, bad_entry)
        self.assertEqual(
            "Invalid file or directory description: %r" % (bad_entry,),
            str(e))


class TestNormalizeShape(testtools.TestCase):

    def test_empty(self):
        # The normal form of an empty list is the empty list.
        empty = normalize_shape([])
        self.assertEqual([], empty)

    def test_sorts_entries(self):
        # The normal form a list of entries is the sorted list of normal
        # entries.
        entries = normalize_shape(['a/b/', 'a/'])
        self.assertEqual([('a/', None), ('a/b/', None)], entries)


class TestCreateNormalShape(testtools.TestCase):

    def test_empty(self):
        tempdir = self.useFixture(TempDir()).path
        create_normal_shape(tempdir, [])
        self.assertThat(tempdir, DirContains([]))

    def test_creates_files(self):
        # When given a list of file specifications, it creates those files
        # underneath the temporary directory.
        path = self.useFixture(TempDir()).path
        create_normal_shape(path, [('a', 'foo'), ('b', 'bar')])
        self.assertThat(path, DirContains(['a', 'b']))
        self.assertThat(os.path.join(path, 'a'), FileContains('foo'))
        self.assertThat(os.path.join(path, 'b'), FileContains('bar'))

    def test_creates_directories(self):
        # When given directory specifications, it creates those directories.
        path = self.useFixture(TempDir()).path
        create_normal_shape(path, [('a/', None), ('b/', None)])
        self.assertThat(path, DirContains(['a', 'b']))
        self.assertThat(os.path.join(path, 'a'), DirExists())
        self.assertThat(os.path.join(path, 'b'), DirExists())

    def test_creates_parent_directories(self):
        # If the parents of a file or directory don't exist, they get created
        # too.
        path = self.useFixture(TempDir()).path
        create_normal_shape(path, [('a/b/', None), ('c/d.txt', 'text')])
        self.assertThat(path, DirContains(['a', 'c']))
        self.assertThat(os.path.join(path, 'a'), DirContains('b'))
        self.assertThat(os.path.join(path, 'a', 'b'), DirExists())
        self.assertThat(os.path.join(path, 'c'), DirExists())
        self.assertThat(os.path.join(path, 'c', 'd.txt'), FileContains('text'))
