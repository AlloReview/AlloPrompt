import re
import yaml
import json
import jinja2
import xmltodict
from alloprompt.utils import (
    reverse_template_auto,
    reverse_template_llm_parse,
    recursive_escape_xml,
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
    return unindent(pattern.findall(xml)[0]).strip()


class Prompt:
    def __init__(
        self,
        path,
        data={},
        data_path=None,
        functions={},
        output_parsing_function="llm_parse",
        default_chat_complete_args={},
    ):
        with open(path, "r") as file:
            template = file.read()
        self.template = {
            "prompt": get_tag_content("prompt", template),
            "output_template": get_tag_content("output_template", template),
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

    def __render(self, inputs):
        inputs = recursive_escape_xml(json.loads(json.dumps(inputs)))
        rendered_prompt = self.environment.from_string(
            self.template["prompt"], self.cache
        ).render(
            input=inputs,
            data=self.data,
            output_template=self.template["output_template"],
            functions=self.functions,
        )
        try:
            rendered_prompt = xmltodict.parse(rendered_prompt)["root"]
        except Exception as e:
            print(rendered_prompt)
            raise e
        return rendered_prompt

    def chat_complete(self, inputs, client, debug=False, *args, **kwargs):
        rendered_prompt = self.__render(inputs)
        if debug:
            print("Messages:")
            print(
                yaml.dump(
                    rendered_prompt["messages"], default_style="|", sort_keys=False
                )
            )
        chat_complete_args = {**self.default_chat_complete_args, **kwargs}
        response = (
            client.chat.completions.create(
                messages=rendered_prompt["messages"], *args, **chat_complete_args
            )
            .choices[0]
            .message.content
        )
        if debug:
            print("Response:")
            print(response)
        try:
            return self.reverse_template(
                response, self.template["output_template"], self.cache
            )
        except Exception as e:
            raise Exception(f'Error "{e}" while parsing the response:\n{response}')

    def print_as_json(self, inputs=None):
        print(json.dumps(self.__render(inputs), indent=2))
