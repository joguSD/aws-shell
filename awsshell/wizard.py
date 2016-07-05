import json
import jmespath
import botocore.session
from botocore import xform_name


class WizardException(Exception):
    pass


class Wizard(object):

    def __init__(self, filename=None):
        self._env = Environment()
        if filename:
            self.load_from_json(filename)

    # Loads the wizards from the spec in dict form
    def load_from_dict(self, spec):
        self.start_stage = spec.get('StartStage', None)
        if not self.start_stage:
            raise WizardException("Start stage not specified")
        self.stages = {}
        for s in spec['Stages']:
            stage = Stage(s, self._env)
            self.stages[stage.name] = stage

    # TODO temporary loader from file, will likely deprecate this when
    # there's a systemic way of loading all wizards in specified locations
    def load_from_json(self, filename):
        with open(filename, 'r') as f:
            spec = json.load(f)
            self.load_from_dict(spec)

    # Performs the basic loop for progressing stages
    def execute(self):
        current_stage = self.start_stage
        while current_stage:
            stage = self.stages.get(current_stage, None)
            if not stage:
                raise WizardException("Stage not found: %s" % current_stage)
            stage.execute()
            current_stage = stage.get_next_stage()


class Stage(object):

    def __init__(self, spec, env):
        self._wizard_env = env
        self.name = spec.get('Name', None)
        self.prompt = spec.get('Prompt', None)
        self.retrieval = spec.get('Retrieval', None)
        self.next_stage = spec.get('NextStage', None)
        self.resolution = spec.get('Resolution', None)
        self.interaction = spec.get('Interaction', None)

    def __handle_static_retrieval(self):
        return self.retrieval.get('Resource')

    def __handle_request_retrieval(self):
        # TODO very basic requests... refactor needed
        req = self.retrieval['Resource']
        # initialize botocore session and client for service in the request
        session = botocore.session.get_session()
        client = session.create_client(req['Service'])
        # get the operation from the client
        operation = getattr(client, xform_name(req['Operation']))
        # get any parameters
        parameters = req.get('Parameters', {})
        env_parameters = self._resolve_parameters(req.get('EnvParameters', {}))
        # union of parameters and env_parameters, conflicts favor env_params
        parameters = dict(parameters, **env_parameters)
        # execute operation passing all parameters
        result = operation(**parameters)
        if self.retrieval.get('Path'):
            result = jmespath.search(self.retrieval['Path'], result)
        return result

    def _handle_retrieval(self):
        print(self.prompt)
        # In case of no retrieval, empty dict
        if not self.retrieval:
            return {}
        elif self.retrieval['Type'] == 'Static':
            return self.__handle_static_retrieval()
        elif self.retrieval['Type'] == 'Request':
            return self.__handle_request_retrieval()

    def _resolve_parameters(self, keys):
        for key in keys:
            keys[key] = self._wizard_env.retrieve(keys[key])
        return keys

    def _handle_interaction(self, data):
        # TODO actually implement this step
        # if no interaction step, just forward data
        if not self.interaction:
            return data
        elif self.interaction['ScreenType'] == 'SimpleSelect':
            data = data[0]
        elif self.interaction['ScreenType'] == 'SimplePrompt':
            for field in data:
                data[field] = 'random'
        return data

    def _handle_resolution(self, data):
        if self.resolution:
            if self.resolution.get('Path'):
                data = jmespath.search(self.resolution['Path'], data)
            self._wizard_env.store(self.resolution['Key'], data)

    def get_next_stage(self):
        if not self.next_stage:
            return None
        elif self.next_stage['Type'] == 'Name':
            return self.next_stage['Name']
        elif self.next_stage['Type'] == 'Variable':
            return self._wizard_env.retrieve(self.next_stage['Name'])

    # Executes all three steps of the stage
    def execute(self):
        retrieved = self._handle_retrieval()
        transformed = self._handle_interaction(retrieved)
        self._handle_resolution(transformed)


class Environment(object):

    def __init__(self):
        self._variables = {}

    def store(self, key, val):
        self._variables[key] = val

    def retrieve(self, path):
        return jmespath.search(path, self._variables)
