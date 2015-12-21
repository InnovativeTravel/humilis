#!/usr/bin/env python
# -*- coding: utf-8 -*-


from click.testing import CliRunner
import humilis
import humilis.cli
import pytest
import os


ENV_ACTIONS = ['create', 'delete']
LOG_LEVELS = ['critical', 'error', 'warning', 'info', 'debug']


@pytest.yield_fixture(scope="module")
def runner():
    yield CliRunner()


@pytest.yield_fixture(scope="module")
def humilis_example_environment():
    yield os.path.join('examples', 'example-environment.yml')


def test_actions(runner, humilis_example_environment):
    for action in ENV_ACTIONS:
        result = runner.invoke(humilis.cli.main, [action,
                                                  '--pretend',
                                                  humilis_example_environment])
        assert result.exit_code == 0


def test_actions_with_missing_environment(runner):
    for action in ENV_ACTIONS:
        result = runner.invoke(humilis.cli.main, [action])
        assert result.exit_code > 0
        assert isinstance(result.exception, SystemExit)


def test_invalid_log_level(runner):
    result = runner.invoke(humilis.cli.main, ['--log', 'invalid'])
    assert result.exit_code > 0
    assert isinstance(result.exception, SystemExit)


def test_valid_log_level(runner, humilis_example_environment):
    for level in ['critical', 'error', 'warning', 'info', 'debug']:
        result = runner.invoke(humilis.cli.main, ['--log', level, 'create',
                                                  humilis_example_environment,
                                                  '--pretend'])
        assert result.exit_code == 0


def test_invalid_botolog_level(runner, humilis_example_environment):
    result = runner.invoke(humilis.cli.main, ['--botolog', 'invalid', 'create',
                                              humilis_example_environment,
                                              '--pretend'])
    assert result.exit_code > 0
    assert isinstance(result.exception, SystemExit)


def test_valid_botolog_level(runner, humilis_example_environment):
    for level in LOG_LEVELS:
        result = runner.invoke(humilis.cli.main, ['--botolog', level, 'create',
                                                  humilis_example_environment,
                                                  '--pretend'])
        assert result.exit_code == 0


def test_output(runner, humilis_example_environment):
    result = runner.invoke(humilis.cli.create, [humilis_example_environment,
                                                '--output', 'filename',
                                                '--pretend'])
    assert result.exit_code == 0


def test_invalid_option(runner, humilis_example_environment):
    result = runner.invoke(humilis.cli.create, [humilis_example_environment,
                                                '--invalid_option', 'whatever'
                                                '--pretend'])
    assert result.exit_code > 0
