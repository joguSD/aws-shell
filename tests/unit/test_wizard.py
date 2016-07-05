import pytest
from awsshell.wizard import Environment, Stage


@pytest.fixture
def env():
    env = Environment()
    env.store('env_var', {'epic': 'nice'})
    return env


# Test that the environment properly stores the given var
def test_environment_store(env):
    assert env._variables.get('env_var') == {'epic': 'nice'}


# Test that the env can retrieve keys via jmespath queries
def test_environment_retrieve(env):
    assert env.retrieve('env_var') == {'epic': 'nice'}
    assert env.retrieve('env_var.epic') == 'nice'


# Test that the env is properly converted into a formatted string
def test_environment_to_string(env):
    display_str = '{\n    "env_var": {\n        "epic": "nice"\n    }\n}'
    assert str(env) == display_str


@pytest.fixture
def stage_spec():
    return {
        'Name': 'ApiSourceSwitch',
        'Prompt': 'Prompting',
        'Retrieval': {
            'Type': 'Static',
            'Resource': [
                {'Option': 'Create new Api', 'Stage': 'CreateApi'},
                {
                    'Option': 'Generate new Api from swagger spec file',
                    'Stage': 'NewSwaggerApi'
                }
            ]
        },
        'Interaction': {'ScreenType': 'SimpleSelect'},
        'Resolution': {'Path': 'Stage', 'Key': 'CreationType'},
        'NextStage': {'Type': 'Variable', 'Name': 'CreationType'}
    }


# Test that the spec is translated to the correct attrs
def test_from_spec(stage_spec):
    test_env = Environment()
    stage = Stage(stage_spec, test_env)
    assert stage.prompt == 'Prompting'
    assert stage.name == 'ApiSourceSwitch'
    assert stage.retrieval == stage_spec['Retrieval']
    assert stage.next_stage == stage_spec['NextStage']
    assert stage.resolution == stage_spec['Resolution']
    assert stage.interaction == stage_spec['Interaction']


# Test that static retrieval reads the data straight from the spec
def test_static_retrieval(stage_spec):
    test_env = Environment()
    stage = Stage(stage_spec, test_env)
    ret = stage._handle_retrieval()
    assert ret == stage_spec['Retrieval']['Resource']


# Test that static retrieval reads the data and can apply a JMESpath query
def test_static_retrieval_with_query(stage_spec):
    stage_spec['Retrieval']['Path'] = '[0].Stage'
    test_env = Environment()
    stage = Stage(stage_spec, test_env)
    ret = stage._handle_retrieval()
    assert ret == 'CreateApi'


# Test that resolution properly puts the resolved value into the env
def test_handle_resolution(stage_spec):
    test_env = Environment()
    stage = Stage(stage_spec, test_env)
    data = {'Stage': 'EpicNice'}
    stage._handle_resolution(data)
    assert test_env.retrieve('CreationType') == 'EpicNice'


# Test that env paramaters can be resolved for the stage
def test_resolve_parameters(stage_spec):
    test_env = Environment()
    test_env.store('Epic', 'Nice')
    test_env.store('Test', {'k': 'v'})
    keys = {'a': 'Epic', 'b': 'Test.k'}
    stage = Stage(stage_spec, test_env)
    resolved = stage._resolve_parameters(keys)
    assert resolved == {'a': 'Nice', 'b': 'v'}


# Test that the stage can resolve the next stage from env
def test_next_stage_resolution(stage_spec):
    test_env = Environment()
    stage = Stage(stage_spec, test_env)
    stage._handle_resolution({'Stage': 'EpicNice'})
    assert stage.get_next_stage() == 'EpicNice'


# Test that the stage can resolve static next stage
def test_next_stage_static(stage_spec):
    test_env = Environment()
    stage_spec['NextStage'] = {'Type': 'Name', 'Name': 'NextStageName'}
    stage = Stage(stage_spec, test_env)
    assert stage.get_next_stage() == 'NextStageName'
