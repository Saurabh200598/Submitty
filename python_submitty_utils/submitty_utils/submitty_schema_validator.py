"""For use in validating submitty configuration objects against json schemas."""


import sys
import json
import jsonschema
from jsonschema import validate
import jsonref


class SubmittySchemaException(Exception):
    """An exception capable of printing helpful information about schema errors."""

    def __init__(self, config_json, schema, message, title, schema_error):
        """Use to aid in printing helpful information about schema errors."""
        super(SubmittySchemaException, self).__init__(schema_error.message)
        self.config_json = config_json
        self.schema = schema
        self.my_message = message
        self.title = title
        self.schema_message = schema_error.message

    def print_human_readable_error(self):
        """Use to print a human readable version of this exception."""
        print(file=sys.stderr)
        print(f'{self.my_message}:', file=sys.stderr)
        if self.schema_message is not None:
            print(self.schema_message, file=sys.stderr)
            print(("The portion of your configuration that caused "
                   "the error is:"), file=sys.stderr)
            print(json.dumps(self.config_json, indent=4), file=sys.stderr)


def complete_config_validator(j_, s_, warn=True):
    """
    Validate a complete configuration against a schema.

    Given a complete config and a complete config schema, validate
    the complete config one piece at a time. On error, raise a
    SubmittySchemaException, which is capable of printing a
    human readable error message.
    """
    s_prop = s_['properties']

    for key in ['autograding', 'autograding_method', 'container_options',
                'resource_limits']:
        validate_schema(j_, s_prop, key, 'global', warn=warn)

    # test all of the global pieces of the config.
    testcases = j_["testcases"]
    t_s = s_['definitions']['testcase']
    p_s = s_['definitions']['testcase']['properties']
    sub_limit_schema = s_['definitions']['submission_limit']
    filecheck_schema = s_['definitions']['filecheck']
    c_schema = s_['definitions']['container']
    abs_v_schema = s_['definitions']['abstract_validation_object']
    spec_v_schema = s_['definitions']['validator_definitions']

    testcase_num = 1
    # validate each testcase one piece at a time.
    for t in testcases:
        # A hack because a testcase can be either a submission_limit, a
        # filecheck, or a regular testcase. We check sub-limit first and
        # short circuit.
        success = False
        for extra_schema in [sub_limit_schema, filecheck_schema]:
            try:
                validate_schema(t, extra_schema, required=False, warn=warn)
                testcase_num += 1
                success = True
            except SubmittySchemaException:
                pass
        if success:
            continue

        # validate all of the different chunks of the testcase
        t_name = f'testcase_{testcase_num}'

        for key in ['dispatcher_actions', 'actions', 'points', 'type',
                    'pre_commands', 'single_port_per_container',
                    'use_router', 'title', 'hidden', 'extra_credit',
                    'input_generation_commands', 'executable_name',
                    'testcase_label']:
            validate_schema(t, p_s, key, t_name, warn=warn)

        containers = t['containers']
        # validate each container in the testcase
        for c in containers:
            validate_schema(c, c_schema, prefix=t_name, warn=warn)

        solution_containers = t['solution_containers']
        for c in solution_containers:
            validate_schema(c, c_schema, prefix=t_name, warn=warn)

        validators = t['validation']
        validator_num = 0
        # Validate each validation object in the testcase
        for v in validators:
            validate_schema(v, abs_v_schema, prefix=t_name, warn=warn)
            validate_schema(v, spec_v_schema, prefix=t_name, warn=warn)
            validator_num += 1
        testcase_num += 1

        validate_schema(t, t_s, prefix=t_name, warn=warn)
    # Finally, validate the config as a whole.
    validate_schema(j_, s_, prefix='Your config json', warn=warn)


def validate_schema(j_, s_, key='', prefix='', required=True, warn=False):
    """
    Validate a configuration against a schema.

    A function which validates a key within a config and a schema.
    If no key is given, we evaluate the whole config or schema.
    """
    descriptive_title = f'{prefix} {key}'
    if key != '':
        my_json_chunk = j_.get(key, None) if j_ is not None else j_
        my_schema = s_.get(key, None) if s_ is not None else s_
    else:
        my_json_chunk = j_
        my_schema = s_
    # If attempting to validate an item not specified in the schema, fail.
    if my_schema is None:
        msg = (f"ERROR: There is no specification for {key} in the schema.",
               " Please add a specification.")
        raise SubmittySchemaException(j_,
                                      s_,
                                      msg,
                                      descriptive_title,
                                      None)
    if my_json_chunk is None:
        if warn:
            print(f"WARNING: could not identify {descriptive_title} ({key})")
        return
    try:
        # validate.
        validate(instance=my_json_chunk, schema=my_schema)
    except jsonschema.exceptions.ValidationError as e:
        msg = f'ERROR: {descriptive_title} was not properly formatted'
        raise SubmittySchemaException(my_json_chunk,
                                      my_schema,
                                      msg,
                                      descriptive_title,
                                      e)


def validate_complete_config_schema_using_filenames(config_path,
                                                    schema_path,
                                                    warn=False):
    """
    Call validate_config after reading in config and schema files.

    Given a path to a complete configuration and a schema, this function
    loads both and validates the configuration against the schema. On
    failure, an exception is thrown, else, nothing is returned.
    """
    with open(schema_path, 'r') as infile:
        schema = jsonref.load(infile)

    with open(config_path, 'r') as infile:
        config_json = json.load(infile)

    complete_config_validator(config_json, schema, warn)
