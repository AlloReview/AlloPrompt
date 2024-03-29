import yaml
import json

code_gen_client = None
parse_client = None
code_gen_model = "gpt-4-turbo-preview"
parse_model = "gpt-3.5-turbo"


def set_code_gen_client(client):
    global code_gen_client
    code_gen_client = client


def set_parse_client(client):
    global parse_client
    parse_client = client


def set_client_llm(client):
    global code_gen_client
    global parse_client
    code_gen_client = client
    parse_client = client


def set_code_gen_model(model):
    global code_gen_model
    code_gen_model = model


def reverse_template_code(template, additional_messages=[]):
    if code_gen_client is None:
        raise ValueError("Please set the code_gen_client variable to the ChatCompletion client")
    messages = (
        [
            {
                "role": "system",
                "content": "Your task is given a Jinja2 template, write a function named `reverse` that takes in the rendered string template and returns the context. You must also write a function named `test` that allow you to test and debug your code. In the `test` function you must print all what's needed to debug the `reverse`function. You must also assert the tests. All the functions must be self-contained.\nThe task of writing a function to reverse-engineer a Jinja2 template involves creating a Python function capable of taking a rendered HTML string, which was originally generated by a Jinja2 template, and extracting specific variables and their values from it. This function must identify the placeholders and structures that were used in the template and map them back to their original variable names and formats, essentially reconstructing the dynamic parts of the template from the static HTML.\n\nThe function's core objectives include:\n\n1. **Pattern Recognition**: It must use precise pattern matching techniques, likely regular expressions, to identify the variable content within the rendered HTML. This involves recognizing the specific HTML tags and text patterns that correspond to Jinja2 variable outputs and control structures.\n\n2. **Variable Extraction**: It should extract variable values accurately, distinguishing between different types of variables, such as single placeholders (`{{ variable }}`) and looped content (`{% for item in list %}`), and reconstructing them into their original format.\n\n3. **Error Handling**: The function needs robust error handling to manage cases where the HTML structure does not match expected patterns, ensuring graceful failures without crashing or producing misleading outputs.\n\n4. **Output Structure**: The extracted variables and their values should be returned in a well-structured format, such as a dictionary, where each key represents a variable name from the template, and the corresponding value is the extracted content.\n\n5. **Robustness**: The function should be robust and anticipate slight change in the output format, such as variations in whitespace etc ... It should understand and focus on the core elements and structure of the output, rather than relying on exact string matching.\n\nThis task requires a deep understanding of both the Jinja2 template syntax and the HTML output structure. It's a complex and error-prone process due to the one-way nature of template rendering, the potential variability in HTML formatting, and the inherent loss of template metadata in the rendered output.\n\nYou must only output the code with code comments to help you in your thinking.\nYou must always first write `test` then `reverse`\nConsider that re and json are already imported.\nWhen given test output with \"test_output:\", you must rewrite both functions with the fixes needed.\nYour output must always take the following format:\n```\ndef test():\n  <test function reverse in different cases>\n\ndef reverse(rendered_str):\n  <reversing_code>\n```",
            },
            {
                "role": "user",
                "content": "Items List:\n{% for item in items %}\n- Name: {{ item.name }}, Quantity: {{ item.quantity }}\n{% endfor %}",
            },
            {
                "role": "assistant",
                "content": "def test():\n    # Test case 1: Two items in the list\n    rendered_str1 = \"Items List:\\n- Name: Apples, Quantity: 5\\n- Name: Oranges, Quantity: 10\\n\"\n    expected_output1 = {'items': [{'name': 'Apples', 'quantity': '5'}, {'name': 'Oranges', 'quantity': '10'}]}\n    assert json.load(json.dumps(reverse(rendered_str1))) == json.load(json.dumps(expected_output1)), f\"Test 1 failed. Output: {reverse(rendered_str1)}\"\n    \n    # Test case 2: Empty list\n    rendered_str2 = \"Items List:\\n\"\n    expected_output2 = {'items': []}\n    assert json.load(json.dumps(reverse(rendered_str2))) == json.load(json.dumps(expected_output2)), f\"Test 2 failed. Output: {reverse(rendered_str2)}\"\n    \n    # Test case 3: One item in the list\n    rendered_str3 = \"Items List:\\n- Name: Bananas, Quantity: 20\\n\"\n    expected_output3 = {'items': [{'name': 'Bananas', 'quantity': '20'}]}\n    assert json.load(json.dumps(reverse(rendered_str3))) == json.load(json.dumps(expected_output3)), f\"Test 3 failed. Output: {reverse(rendered_str3)}\"\n    \n    print(\"All tests passed!\")\n\ndef reverse(rendered_str):\n    # Initialize an empty list to hold item dictionaries\n    items = []\n    \n    # Define the regular expression pattern to match each item's details\n    pattern = r\"- Name: (.*), Quantity: (\\d+)\"\n    \n    # Find all matches of the pattern in the rendered string\n    matches = re.findall(pattern, rendered_str)\n    \n    # Iterate over the matches and construct the item dictionaries\n    for match in matches:\n        name, quantity = match\n        items.append({'name': name, 'quantity': quantity})\n    \n    # Return the reconstructed context\n    return {'items': items}\n\n# Uncomment to run tests\n# test()",
            },
        ]
        + [{"role": "user", "content": template}]
        + additional_messages
    )
    chat_completion = code_gen_client.chat.completions.create(
        messages=messages, model=code_gen_model, temperature=0, max_tokens=2048
    )
    if "```python" in chat_completion.choices[0].message.content:
        return chat_completion.choices[0].message.content.split("```python")[1].split("```")[0].strip()
    if "```" in chat_completion.choices[0].message.content:
        return chat_completion.choices[0].message.content.split("```")[1].strip()
    return chat_completion.choices[0].message.content.strip()


def check_code(code, template, depth=0):
    if depth > 3:
        print("Not able to fix !")
        return code
    captured_print = []

    def capture_print(*args, **kwargs):
        # Capture the print output into a variable instead of printing it
        captured_print.append(" ".join(map(str, args)))

    try:
        functions = {}
        functions["print"] = capture_print
        code = "import re\nimport json\n" + code
        exec(code, functions)
        functions["test"]()
    except Exception:
        print("Error, rewriting the code ...")
        import traceback

        captured_print.append(str(traceback.format_exc()))
        print("\n".join(captured_print))
        code = reverse_template_code(
            template,
            [
                {"role": "assistant", "content": "```python\n" + code + "\n```"},
                {
                    "role": "user",
                    "content": "test_output:\n" + "\n".join(captured_print),
                },
            ],
        )
        print("Rewritting the code ...")
        return check_code(code, template, depth + 1)
    return code


def reverse_template_auto(rendered_template, template, cache={}):
    if template in cache:
        code = cache[template]
    else:
        code = reverse_template_code(template)
        for i in range(3):
            code = check_code(code, template)
        cache[template] = code

    functions = {}
    code = "import re\nimport json\n" + code
    exec(code, functions)

    return functions["reverse"](rendered_template)


def reverse_template_llm_parse(rendered_template, template, *args, **kwargs):
    if parse_client is None:
        raise ValueError("Please set the code_gen_client variable to the ChatCompletion client")
    response = parse_client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": 'Your task is given a Jinja2 template and a rendered output, return the JSON representation of the template.\n      The JSON must have the format: {"values": {~json of the extracted variables~}}',
            },
            {
                "role": "user",
                "content": "Jinja2 template:\n      Grocery List:\n{% for item in grocery_list %}\n- {{item.name}}: {{item.quantity}} (Brand: {{item.brand}})\n{% endfor %}\n      Rendered output:\n      \nGrocery List:\n- Milk: 2 liters (Brand: Dairy Fresh)\n- Bread: 1 loaf (Brand: Baker's Delight)\n- Apples: 5 (Brand: Orchard Pure)",
            },
            {
                "role": "assistant",
                "content": '{"values":  {"grocery_list": [{"name": "Milk", "quantity": "2 liters", "brand": "Dairy Fresh"}, {"name": "Bread", "quantity": "1 loaf", "brand": "Baker\'s Delight"}, {"name": "Apples", "quantity": "5", "brand": "Orchard Pure"}]} }',
            },
            {
                "role": "user",
                "content": "Jinja2 template:\n      settings:\n  brightness: {{ brightness }}\n  contrast: {{ contrast }}\n  hue: {{ hue }}\n  saturation: {{ saturation }}\n      Rendered output:\n      \nsettings:\n  brightness: 50\n  contrast: 70\n  hue: 0\n  saturation: 40",
            },
            {
                "role": "assistant",
                "content": '{"values":  {"brightness": 50, "contrast": 70, "hue": 0, "saturation": 40} }',
            },
        ]
        + [
            {
                "role": "user",
                "content": f"Jinja2 template:\n{template}\nRendered output:\n{rendered_template}",
            }
        ],
        model=parse_model,
        temperature=0,
        response_format={"type": "json_object"},
    )

    return json.loads(response.choices[0].message.content)["values"]


def escape_xml_characters(input_string):
    """
    Escapes characters that have special meaning in XML.

    Args:
        input_string (str): The string to be escaped.

    Returns:
        str: The escaped string where characters like '<', '>', '&', '"', and "'" are replaced with their corresponding XML entities.
    """
    return (
        input_string.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def recursive_escape_xml(input_object):
    """
    Recursively navigate through any string, object, or array and apply escape_xml_characters to every string.

    Args:
        input_object (str, list, dict): The input that may contain strings to be escaped.

    Returns:
        The input object with all its strings XML-escaped.
    """
    if isinstance(input_object, str):
        return escape_xml_characters(input_object)
    elif isinstance(input_object, list):
        return [recursive_escape_xml(item) for item in input_object]
    elif isinstance(input_object, dict):
        return {key: recursive_escape_xml(value) for key, value in input_object.items()}
    else:
        return input_object  # If it's not a string, list, or dict, return it unchanged.


def str_presenter(dumper, data):
    if "\n" in data:  # check for presence of newline character
        # Strip leading and trailing whitespace from each line
        data = "\n".join([line.rstrip() for line in data.strip().splitlines()])
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


yaml.add_representer(str, str_presenter)


def convert_dict_to_yaml(data_dict):
    return yaml.dump(data_dict, sort_keys=False, default_flow_style=False, allow_unicode=True)


def otag(tag):
    return f"&lt;{tag}&gt;"


def ctag(tag):
    return f"&lt;/{tag}&gt;"
