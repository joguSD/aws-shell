AWS Shell - Wizards
==================================

Wizards
-------
A `Wizard` is a collection of `Stages` that achieve a higher level goal on one or
more Amazon Web Services. Wizards are defined in JSON with the following format:
```
{
  "StartStage": "StageName",
  "Stages": [...]
}
```
Key | Description
----|------------
StageStage | The name of the `Stage` that begins the `Wizard`.
Stages | The list of all `Stage` definitions.

Stages
------
### Overview
A `Stage` is a sequence of steps to be executed that perform a specific task or
operation. The model is defined as follows:
```
{
  "Name": "StageName",
  "Prompt": "StagePrompt",

  "Retrieval": {...},
  "Interaction": {...},
  "Resolution": {...},

  "NextStage": {...}
}
```
Key | Description
----|------------
Name | The name of the `Stage`.
Prompt | A descriptive prompt used during the `Interaction` step.
Retrieval | *(Optional)* The first of three steps which defines the data source to be used in this `Stage`. If `Retrieval` is omitted the data defaults to `{}`.
Interaction | *(Optional)* The second step which receives the data retrieved in the `Retrieval` step and allows the customer to manipulate this data in a defined manner. For a list of possible `Interactions` see below. If the `Interaction` is omitted no transformation is applied and the data is forwarded to `Resolution`.
Resolution | *(Optional)* The final step in a stage. `Resolution` receives the data after the customer has interacted with it and stores that final result in the `Environment`. If the `Resolution` is omitted nothing is stored into the `Environment` and the data from `Interaction` is used as the resulting data for this `Stage`.
NextStage | *(Optional)* Specifies the name of the stage to be executed next. The next stage can be specified as a static name or dynamic resolution from the `Environment`. If omitted the `Wizard` will halt execution and return the result of this final stage as the result of the `Wizard`.

### Retrieval
A `Retrieval` has the following structure:
```
{
  "Type": "RetrievalType",
  "Resource": {...}
}
```
Key | Description
----|------------
Type | The type of `Retrieval`. There are currently three types: `Static`, `Request`, `Wizard`.
Resource | Defines the details for the specified `Type`.
Path | *(Optional)* A JMESPath query that can optionally be applied to the retrieved data transforming it before being passed on to the `Interaction`. This can be applied to any type of `Retrieval`.

#### Static
A `Static` `Retrieval` will treat the value of the `Resource` key literally.
The value of the `Resource` will be treated as the data source and passed on to
the `Interaction` step. This is useful for selecting an option from a static
list of options or branching the `Wizard` by allowing the customer to select
a `Stage`. For example:
```
{
  "Type": "Static",
  "Resource": [
    { "Option": "Do not use profile", "Stage": "SelectSubnetSwitch"},
    { "Option": "Select a profile", "Stage": "GetInstanceProfile"}
  ]   
}
```
This data could be used in an `Interaction` to allow the customer to select a
`StageName` from a list of options.

#### Request
A `Request` `Retrieval` will perform an AWS operation call via `botocore`.
The result of the operation call will be treated as the data source and given
to the `Interaction` step. An example `Request` might look like:
```
{
  "Service": "ec2",
  "Operation": "RunInstances",
  "Parameters": { "DryRun": true },
  "EnvParameters": {
      "ImageId": "ImageId",
      "SubnetId": "SubnetId",
      "SecurityGroupIds": "GroupId | [@]",
      "IamInstanceProfile": "Profile | {Name: @.InstanceProfileName}"
  }
}
```
Key | Description
----|------------
Service | The service to use when creating a `botocore` client.
Operation | The operation to be called on the `botocore` client.
Parameters | The value of this key is expected to be a JSON Object and is taken literally providing static parameters that will not change between `Wizard` executions.
EnvParameters | The value of this key is expected to be a JSON Object where each key is a parameter and each value is a JMESPath query that will be applied to the `Environment` to allow a result from a previous `Stage` to be used as a parameter in this `Request`. **Note**: Only the top level of keys will be evaluated, and behavior for values other than a string which represents a JMESPath query is undefined. Recursive parameter resolution is a possible extension. For now, more complex JMESPath queries can bridge the gap.

#### Wizard
A `Wizard` `Retrieval` will delegate to another `Wizard` and use the resulting data as the source to be given to `Interaction`. This form of `Wizard` delegation allows one to write specific and reusable `Wizards`. This is useful for operations that requirement many parameters that have dependencies on potentially more than one service. An example:
```
{
  "Type": "Wizard",
  "Resource": "create-instance-profile",
  "Path": "InstanceProfile"
}
```
In the above example the `create-instance-profile` wizard will walk the customer
through the creation of an InstanceProfile and return the response data. That
response data then has the `"InstanceProfile"` query applied to it resulting in
just the created resource being passed onto the next step.

### Interactions
The structure of an `Interaction`:
```
{
  "ScreenType": "InteractionName",
  ...
}
```
Key | Description
----|------------
ScreenType | The name of the specific `Interaction` to be used.

Depending on the `ScreenType` additional keys may be required.

#### SimpleSelect
Display a list of options, allowing the user to select one.

Given a list of one or more items, display them in a dropdown selection
menu and allows the user to pick one. If a path is present on the
interaction the path will be applied to the list transforming it into a list
of strings to be used when displaying each option. Upon selection, the related
item is returned. If no path is present, the list is assumed to be of strings
and used as is. Example:
```
{
  "ScreenType": "SimpleSelect",
  "Path": "[].Option"
}
```
This example will convert the list of options to a list of display strings by
using the `Option` key for each item.

**Note**: `SimpleSelect` expects a non-empty list.

TODO: IMAGE


#### InfoSelect
Display a list of options with meta information.

Small extension of `SimpleSelect` that displays what the complete object looks
like rendered as JSON in a pane below the prompt, providing more context on each
option. Definition structure is the same as `SimpleSelect`.

**Note**: `InfoSelect` expects a non-empty list.

TODO: IMAGE


#### FuzzySelect
Typing will apply a case sensitive fuzzy filter to the options.

Show completions based on the given list of options, allowing the user to
type to begin filtering the options with a fuzzy search. The prompt will
also validate that the input is from the list and will reject all other
inputs. Definition structure is the same as `SimpleSelect`.

**Note**: `InfoSelect` expects a non-empty list.
**Note**: If there are duplicate options after the application of a JMESPath
query it is no longer possible to differentiate and there maybe conflicts. It's
best to use display strings that will be unique.

TODO: IMAGE


#### FilePrompt
Prompt the user to select a file.

Provide completions to the current path by suggesting files or directories
in the last directory of the current path. Upon selection returns the
contents of the file as the result of the interaction. Example:
```
{
  "ScreenType": "FilePrompt"
}
```
This type of `Interaction` is useful when an operation expects a file blob.

TODO: IMAGE


#### SimplePrompt
Prompt the user to type in responses for each field.

Each key on the provided object is considered a field and the user will be
prompted for input for each key. The provided input replaces the value for
each key creating a completed object of key to user input. Example:
```
{
  "ScreenType": "SimplePrompt"
}
```
An example of what data is expected (typically this will come from a `Static`
`Retrieval`):
```
{
  "FieldOne": "",
  "FieldTwo": ""
}
```
After the `Interaction` the data will be transformed to:

```
{
  "FieldOne": "User input for FieldOne",
  "FieldTwo": "User input for FieldTwo"
}
```

**Note**: All input from a `SimplePrompt` will be a string. If this input will
be used as a parameter to an operation where the parameter expects a different
type there will be a 'best attempt' coercion to make the string the appropriate
type. Currently, this will coercion will attempt to make strings into the
appropriate numerical type (int, long, float, double).

TODO: IMAGE

### Resolution
The `Resolution` step is structured as follows:
```
{
  "Path": "Instances",
  "Key": "EC2Instances"
}
```
Key | Description
----|------------
Key | A variable name specifying what the data should be saved into the `Environment` as.
Path | A final JMESPath query to be applied before the data is stored into the `Environment`.

For example if the following data was given to the `Resolution` step:
```
{
  "ResponseMetaData": {...},
  "Instances": ["instance1", "instance2"],
  ...
}
```
The above `Resolution` would result in the following data:
```
"Instances": ["instance1", "instance2"]
```
Which would be stored into the `Environment` like so:
```
{
  "EC2Instances": ["instance1", "instance2"],
  ...
}
```


### NextStage
The next stage can be specified in one of two ways: by supplying a static
`StageName` or by supplying a JMESPath query that will be applied to the
`Environment` and return a `StageName` stored by a previous `Stage`. If the
`NextStage` key is omitted the current `Stage` will be the last and `Wizard`
execution will halt. The `NextStage` key has the following structure:
```
{
  "Type": "Name" | "Variable",
  "Name": "StaticNameOrVariable"
}
```
Key | Description
----|------------
Type | The value for this key is either `"Name"` or `"Variable"`.
Name | If the type is `Name` this value will be taken literally, else if the type is `Variable` this value will be treated as a JMESPath query that will return the `StageName` when applied to the `Environment`.


Simple Example
--------------
```
{
  "StartStage": "GetTopic",
  "Stages": [
    {
      "Name": "GetTopic",
      "Prompt": "Select the topic to publish to:",

      "Retrieval": {
        "Type": "Request",
        "Resource": {
          "Service": "sns",
          "Operation": "ListTopics"
        },
        "Path": "Topics"
      },

      "Interaction": {
        "ScreenType": "SimpleSelect",
        "Path": "[].TopicArn"
      },

      "Resolution": {
        "Key": "TopicArn",
        "Path": "TopicArn"
      },

      "NextStage": { "Type": "Name", "Name": "MessageForm" }
    },

    {
      "Name": "MessageForm",
      "Prompt": "Prove the message details.",

      "Retrieval": {
        "Type": "Static",
        "Resource": {
          "Subject": "",
          "Body": ""
        }
      },

      "Interaction": { "ScreenType": "SimplePrompt" },

      "Resolution": { "Key": "MessageDetails" },

      "NextStage": { "Type": "Name", "Name": "PublishMessage" }
    },

    {
      "Name": "PublishMessage",
      "Prompt": "Publishing message...",

      "Retrieval": {
        "Type": "Request",
        "Resource": {
          "Service": "sns",
          "Operation": "Publish",
          "EnvParameters": {
            "TopicArn": "TopicArn",
            "Message": "MessageDetails.Body",
            "Subject": "MessageDetails.Subject"
          }
        }
      }
    }
  ]
}
```
The above wizard will:
  1. Get the list of available sns topics and allow the customer to select one.
  2. Prompt the user to enter their desired subject and message body.
  3. Format and submit the proper request to the sns publish operation.
