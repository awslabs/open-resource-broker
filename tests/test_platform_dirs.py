import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from src.config.platform_dirs import in_virtualenv, get_config_location, get_work_location, get_logs_location


class TestInVirtualenv:
    def test_in_virtualenv_true(self):
        with patch.object(sys, 'prefix', '/path/to/venv'), \
             patch.object(sys, 'base_prefix', '/usr/local'):
            assert in_virtualenv() is True

    def test_in_virtualenv_false(self):
        with patch.object(sys, 'prefix', '/usr/local'), \
             patch.object(sys, 'base_prefix', '/usr/local'):
            assert in_virtualenv() is False


class TestGetConfigLocation:
    def test_development_case(self):
        """Test development case: pyproject.toml exists"""
        with patch('pathlib.Path.cwd') as mock_cwd, \
             patch('pathlib.Path.exists') as mock_exists:
            mock_cwd.return_value = Path('/dev/project')
            mock_exists.return_value = True
            
            result = get_config_location()
            assert result == Path('/dev/project/config')

    def test_virtualenv_case(self):
        """Test virtualenv case: in venv, no pyproject.toml"""
        with patch('pathlib.Path.cwd') as mock_cwd, \
             patch('pathlib.Path.exists') as mock_exists, \
             patch.object(sys, 'prefix', '/project/.venv'), \
             patch.object(sys, 'base_prefix', '/usr/local'):
            mock_cwd.return_value = Path('/dev/project')
            mock_exists.return_value = False
            
            result = get_config_location()
            assert result == Path('/project/config')

    def test_user_install_case(self):
        """Test user install case: sys.prefix under home"""
        with patch('pathlib.Path.cwd') as mock_cwd, \
             patch('pathlib.Path.exists') as mock_exists, \
             patch('pathlib.Path.home') as mock_home, \
             patch.object(sys, 'prefix', '/home/user/.local'), \
             patch.object(sys, 'base_prefix', '/home/user/.local'):
            mock_cwd.return_value = Path('/dev/project')
            mock_exists.return_value = False
            mock_home.return_value = Path('/home/user')
            
            result = get_config_location()
            assert result == Path('/home/user/.local/orb/config')

    def test_system_install_usr_case(self):
        """Test system install case: sys.prefix starts with /usr"""
        with patch('pathlib.Path.cwd') as mock_cwd, \
             patch('pathlib.Path.exists') as mock_exists, \
             patch('pathlib.Path.home') as mock_home, \
             patch.object(sys, 'prefix', '/usr/local'), \
             patch.object(sys, 'base_prefix', '/usr/local'):
            mock_cwd.return_value = Path('/dev/project')
            mock_exists.return_value = False
            mock_home.return_value = Path('/home/user')
            
            result = get_config_location()
            assert result == Path('/usr/local/orb/config')

    def test_system_install_opt_case(self):
        """Test system install case: sys.prefix starts with /opt"""
        with patch('pathlib.Path.cwd') as mock_cwd, \
             patch('pathlib.Path.exists') as mock_exists, \
             patch('pathlib.Path.home') as mock_home, \
             patch.object(sys, 'prefix', '/opt/python'), \
             patch.object(sys, 'base_prefix', '/opt/python'):
            mock_cwd.return_value = Path('/dev/project')
            mock_exists.return_value = False
            mock_home.return_value = Path('/home/user')
            
            result = get_config_location()
            assert result == Path('/opt/python/orb/config')

    def test_fallback_case(self):
        """Test fallback case: none of the above conditions"""
        with patch('pathlib.Path.cwd') as mock_cwd, \
             patch('pathlib.Path.exists') as mock_exists, \
             patch('pathlib.Path.home') as mock_home, \
             patch.object(sys, 'prefix', '/some/other/path'), \
             patch.object(sys, 'base_prefix', '/some/other/path'):
            mock_cwd.return_value = Path('/dev/project')
            mock_exists.return_value = False
            mock_home.return_value = Path('/home/user')
            
            result = get_config_location()
            assert result == Path('/home/user/.orb/config')


class TestGetWorkLocation:
    def test_get_work_location(self):
        """Test work location is config parent + work"""
        with patch('src.config.platform_dirs.get_config_location') as mock_config:
            mock_config.return_value = Path('/base/config')
            
            result = get_work_location()
            assert result == Path('/base/work')


class TestGetLogsLocation:
    def test_get_logs_location(self):
        """Test logs location is config parent + logs"""
        with patch('src.config.platform_dirs.get_config_location') as mock_config:
            mock_config.return_value = Path('/base/config')
            
            result = get_logs_location()
            assert result == Path('/base/logs')