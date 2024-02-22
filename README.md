# AlloPrompt Library

## Overview

`alloprompt` is a Python library tailored for managing and interacting with prompts for language models. It leverages templating to dynamically generate prompts and parse responses, making it ideal for applications that require structured interaction with language models.

## Installation

To use `alloprompt`, you must first install it along with its dependencies:

```bash
pip install jinja2 xmltodict pyyaml
```

## Writing a Prompt Template

Prompt templates in `alloprompt` are written in `.xml.j2` files, which combine XML structure with Jinja2 templating syntax. The .xml.j2 file consists of two main parts:

1. `<prompt>`: This section contains the Jinja2 template for the prompt you want to send to the language model.
2. `<output_template>`: This section defines the expected format of the output from the language model.

Here's an example of what a `.xml.j2` file might look like:

```xml
<prompt>
  <root>
    <messages>
      <role>system</role>
      <content>
        {{ system_message }}
      </content>
    </messages>
    <messages>
      <role>user</role>
      <content>
        {{ user_message }}
      </content>
    </messages>
  </root>
</prompt>
<output_template>
  Questions:
  {% for question in questions %}
  - {{ question.question }}
  {% endfor %}
</output_template>
```

## Using the Prompt Class

To create a prompt, instantiate the `Prompt` class with the path to your template file:

```python
from alloprompt import Prompt

prompt_instance = Prompt("path/to/your/template.xml.j2")
```

### Data Parameter

The parameter `data` in the `Prompt` constructor is a dictionary that provides the data to be used when rendering the template. For example:

```python
data = {
    "system_message": "Please provide a summary of the following text.",
    "user_message": "Artificial intelligence is a branch of computer science..."
}
prompt_instance = Prompt("path/to/your/template.xml.j2", data=data)
```

### Functions Parameter

The `functions` parameter allows you to pass custom functions that can be used within your Jinja2 templates.

### Output Parsing Function

The `output_parsing_function` parameter specifies the method used to parse the output from the language model. It can be set to `None`, `auto`, `llm_parse`, or a custom function.

## Rendering the Prompt

The prompt is rendered using the Jinja2 templating engine, which replaces placeholders in the template with actual data provided in the parameter.

## Chat Completion

The `chat_complete` method sends the rendered prompt to the language model and retrieves the response:

```python
response = prompt_instance.chat_complete(inputs, client, *args, **kwargs)
```

- `inputs`: A dictionary with data to render the prompt.
- `client`: An instance of the OpenAI language model client.
- All the other arguments are the same as for the normal `chat_completion`

## Debugging

The `debug` parameter in `chat_complete` can be set to `True` to print the messages sent to and received from the language model, as well as the parsed output.

## Conclusion

`alloprompt` simplifies the process of generating and parsing prompts for language models, making it a valuable tool for developers working in the field of AI and natural language processing.
