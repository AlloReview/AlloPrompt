import re
import yaml
import json
import jinja2
import xmltodict
from alloprompt.utils import (
    reverse_template_auto,
    reverse_template_llm_parse,
    recursive_escape_xml,
    convert_dict_to_yaml,
    otag,
    ctag,
)


def unindent(text):
    lines = text.split("\n")
    # Remove empty lines
    lines_test = [line for line in lines if line.strip() != ""]
    # Find the minimum indentation (excluding empty lines)
    if len(lines_test) == 0:
        return text
    min_indentation = min(len(line) - len(line.lstrip(" ")) for line in lines_test)
    # Remove the minimum indentation
    return "\n".join(line[min_indentation:] for line in lines)


def get_tag_content(tag, xml):
    pattern = re.compile(rf"<{tag}>(.*?)</{tag}>", re.DOTALL)
    if len(pattern.findall(xml)) == 0:
        return None
    return unindent(pattern.findall(xml)[0]).strip()


class Prompt:
    def __init__(
        self,
        path,
        data={},
        data_path=None,
        functions={},
        output_parsing_function="llm_parse",
        stream_output_parsing_function=lambda x: x,
        default_chat_complete_args={},
        default_client=None,
    ):
        with open(path, "r") as file:
            template = file.read()
        self.template = {
            "prompt": get_tag_content("prompt", template),
            "output_template": get_tag_content("output_template", template),
            "components": (
                xmltodict.parse(get_tag_content("components", template))
                if get_tag_content("components", template)
                else {}
            ),
        }
        if output_parsing_function is None:
            self.reverse_template = lambda response, _, __: response
        if output_parsing_function == "auto":
            self.reverse_template = reverse_template_auto
        if output_parsing_function == "llm_parse":
            self.reverse_template = reverse_template_llm_parse
        if type(output_parsing_function) is type(lambda: None):
            self.reverse_template = output_parsing_function
        self.data = data
        if data_path is not None:
            with open(data_path, "r") as file:
                self.data = {**self.data, **yaml.safe_load(file)}
        self.functions = functions
        self.environment = jinja2.Environment()
        self.cache = {}
        self.default_chat_complete_args = default_chat_complete_args
        self.default_client = default_client
        self.stream_output_parsing_function = stream_output_parsing_function

    def render(self, template, **data):
        return self.environment.from_string(template).render(
            **data, render=lambda t, d: self.render(t, **d), otag=otag, ctag=ctag, to_yaml=convert_dict_to_yaml
        )

    def render_prompt(self, inputs={}, inputs_yaml=None, debug=False):
        if inputs_yaml:
            with open(inputs_yaml, "r") as file:
                inputs = {**yaml.safe_load(file), **inputs}
        inputs = recursive_escape_xml(json.loads(json.dumps(inputs)))
        rendered_prompt = self.render(
            self.template["prompt"],
            input=inputs,
            data=recursive_escape_xml(json.loads(json.dumps(self.data))),
            output_template=self.template["output_template"],
            components=self.template["components"],
            functions=self.functions,
        )
        try:
            rendered_prompt = xmltodict.parse(rendered_prompt)["root"]
        except Exception as e:
            print(rendered_prompt)
            raise e
        if debug:
            print("Messages:")
            print(convert_dict_to_yaml(rendered_prompt["messages"]))
        return rendered_prompt

    def chat_complete(
        self, inputs=None, inputs_yaml=None, client=None, debug=False, output_as_yaml=False, *args, **kwargs
    ):
        if client is None:
            client = self.default_client
        rendered_prompt = self.render_prompt(inputs, inputs_yaml, debug)
        chat_complete_args = {**self.default_chat_complete_args, **kwargs}
        response = client.chat.completions.create(messages=rendered_prompt["messages"], *args, **chat_complete_args)
        if debug:
            print("Response:")
            print(response)
        try:
            if chat_complete_args.get("stream", False):

                def iterate_responses(generator):
                    response_text = ""
                    for response in generator:
                        response_text += response.choices[0].delta.content or ""
                        yield self.stream_output_parsing_function(response_text)

                return iterate_responses(response)
            else:
                response = response.choices[0].message.content
                result = self.reverse_template(response, self.template["output_template"], self.cache)
                if output_as_yaml:
                    return convert_dict_to_yaml(result)
                else:
                    return result
        except Exception as e:
            raise Exception(f'Error "{e}" while parsing the response:\n{response}')

    def print_as_json(self, inputs=None):
        print(json.dumps(self.render(inputs), indent=2))
