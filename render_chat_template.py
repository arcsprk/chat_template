import json
from datetime import datetime
from jinja2 import Environment

# 1. 제공된 Jinja2 템플릿을 문자열로 저장합니다.
template_string = """
{#-  In addition to the normal inputs of `messages` and `tools`, this template also accepts the  following kwargs:  - "builtin_tools": A list, can contain "browser" and/or "python".  - "model_identity": A string that optionally describes the model identity.  - "reasoning_effort": A string that describes the reasoning effort, defaults to "medium". #}{#- Tool Definition Rendering ============================================== #}{%- macro render_typescript_type(param_spec, required_params, is_nullable=false) -%}    {%- if param_spec.type == "array" -%}        {%- if param_spec['items'] -%}            {%- if param_spec['items']['type'] == "string" -%}                {{- "string[]" }}            {%- elif param_spec['items']['type'] == "number" -%}                {{- "number[]" }}            {%- elif param_spec['items']['type'] == "integer" -%}                {{- "number[]" }}            {%- elif param_spec['items']['type'] == "boolean" -%}                {{- "boolean[]" }}            {%- else -%}                {%- set inner_type = render_typescript_type(param_spec['items'], required_params) -%}                {%- if inner_type == "object | object" or inner_type|length > 50 -%}                    {{- "any[]" }}                {%- else -%}                    {{- inner_type + "[]" }}                {%- endif -%}            {%- endif -%}            {%- if param_spec.nullable -%}                {{- " | null" }}            {%- endif -%}        {%- else -%}            {{- "any[]" }}            {%- if param_spec.nullable -%}                {{- " | null" }}            {%- endif -%}        {%- endif -%}    {%- elif param_spec.type is defined and param_spec.type is iterable and param_spec.type is not string and param_spec.type is not mapping and param_spec.type[0] is defined -%}        {#- Handle array of types like ["object", "object"] from Union[dict, list] #}        {%- if param_spec.type | length > 1 -%}            {{- param_spec.type | join(" | ") }}        {%- else -%}            {{- param_spec.type[0] }}        {%- endif -%}    {%- elif param_spec.oneOf -%}        {#- Handle oneOf schemas - check for complex unions and fallback to any #}        {%- set has_object_variants = false -%}        {%- for variant in param_spec.oneOf -%}            {%- if variant.type == "object" -%}                {%- set has_object_variants = true -%}            {%- endif -%}        {%- endfor -%}        {%- if has_object_variants and param_spec.oneOf|length > 1 -%}            {{- "any" }}        {%- else -%}            {%- for variant in param_spec.oneOf -%}                {{- render_typescript_type(variant, required_params) -}}                {%- if variant.description %}                    {{- "// " + variant.description }}                {%- endif -%}                {%- if variant.default is defined %}                    {{ "// default: " + variant.default|tojson }}                {%- endif -%}                {%- if not loop.last %}                    {{- " | " }}                {% endif -%}            {%- endfor -%}        {%- endif -%}    {%- elif param_spec.type == "string" -%}        {%- if param_spec.enum -%}            {{- '"' + param_spec.enum|join('" | "') + '"' -}}        {%- else -%}            {{- "string" }}            {%- if param_spec.nullable %}                {{- " | null" }}            {%- endif -%}        {%- endif -%}    {%- elif param_spec.type == "number" -%}        {{- "number" }}    {%- elif param_spec.type == "integer" -%}        {{- "number" }}    {%- elif param_spec.type == "boolean" -%}        {{- "boolean" }}    {%- elif param_spec.type == "object" -%}        {%- if param_spec.properties -%}            {{- "{\n" }}            {%- for prop_name, prop_spec in param_spec.properties.items() -%}                {{- prop_name -}}                {%- if prop_name not in (param_spec.required or []) -%}                    {{- "?" }}                {%- endif -%}                {{- ": " }}                {{ render_typescript_type(prop_spec, param_spec.required or []) }}                {%- if not loop.last -%}                    {{-", " }}                {%- endif -%}            {%- endfor -%}            {{- "}" }}        {%- else -%}            {{- "object" }}        {%- endif -%}    {%- else -%}        {{- "any" }}    {%- endif -%}{%- endmacro -%}{%- macro render_tool_namespace(namespace_name, tools) -%}    {{- "## " + namespace_name + "\n\n" }}    {{- "namespace " + namespace_name + " {\n\n" }}    {%- for tool in tools %}        {%- set tool = tool.function %}        {{- "// " + tool.description + "\n" }}        {{- "type "+ tool.name + " = " }}        {%- if tool.parameters and tool.parameters.properties %}            {{- "(_: {\n" }}            {%- for param_name, param_spec in tool.parameters.properties.items() %}                {%- if param_spec.description %}                    {{- "// " + param_spec.description + "\n" }}                {%- endif %}                {{- param_name }}                {%- if param_name not in (tool.parameters.required or []) -%}                    {{- "?" }}                {%- endif -%}                {{- ": " }}                {{- render_typescript_type(param_spec, tool.parameters.required or []) }}                {%- if param_spec.default is defined -%}                    {%- if param_spec.enum %}                        {{- ", // default: " + param_spec.default }}                    {%- elif param_spec.oneOf %}                        {{- "// default: " + param_spec.default }}                    {%- else %}                        {{- ", // default: " + param_spec.default|tojson }}                    {%- endif -%}                {%- endif -%}                {%- if not loop.last %}                    {{- ",\n" }}                {%- else %}                    {{- ",\n" }}                {%- endif -%}            {%- endfor %}            {{- "}) => any;\n\n" }}        {%- else -%}            {{- "() => any;\n\n" }}        {%- endif -%}    {%- endfor %}    {{- "} // namespace " + namespace_name }}{%- endmacro -%}{%- macro render_builtin_tools(browser_tool, python_tool) -%}    {%- if browser_tool %}        {{- "## browser\n\n" }}        {{- "// Tool for Browse.\n" }}        {{- "// The `cursor` appears in brackets before each Browse display: `[{cursor}]`.\n" }}        {{- "// Cite information from the tool using the following format:\n" }}        {{- "// `【{cursor}†L{line_start}(-L{line_end})?】`, for example: `【6†L9-L11】` or `【8†L3】`.\n" }}        {{- "// Do not quote more than 10 words directly from the tool output.\n" }}        {{- "// sources=web (default: web)\n" }}        {{- "namespace browser {\n\n" }}        {{- "// Searches for information related to `query` and displays `topn` results.\n" }}        {{- "type search = (_: {\n" }}        {{- "query: string,\n" }}        {{- "topn?: number, // default: 10\n" }}        {{- "source?: string,\n" }}        {{- "}) => any;\n\n" }}        {{- "// Opens the link `id` from the page indicated by `cursor` starting at line number `loc`, showing `num_lines` lines.\n" }}        {{- "// Valid link ids are displayed with the formatting: `【{id}†.*】`.\n" }}        {{- "// If `cursor` is not provided, the most recent page is implied.\n" }}        {{- "// If `id` is a string, it is treated as a fully qualified URL associated with `source`.\n" }}        {{- "// If `loc` is not provided, the viewport will be positioned at the beginning of the document or centered on the most relevant passage, if available.\n" }}        {{- "// Use this function without `id` to scroll to a new location of an opened page.\n" }}        {{- "type open = (_: {\n" }}        {{- "id?: number | string, // default: -1\n" }}        {{- "cursor?: number, // default: -1\n" }}        {{- "loc?: number, // default: -1\n" }}        {{- "num_lines?: number, // default: -1\n" }}        {{- "view_source?: boolean, // default: false\n" }}        {{- "source?: string,\n" }}        {{- "}) => any;\n\n" }}        {{- "// Finds exact matches of `pattern` in the current page, or the page given by `cursor`.\n" }}        {{- "type find = (_: {\n" }}        {{- "pattern: string,\n" }}        {{- "cursor?: number, // default: -1\n" }}        {{- "}) => any;\n\n" }}        {{- "} // namespace browser\n\n" }}    {%- endif -%}    {%- if python_tool %}        {{- "## python\n\n" }}        {{- "Use this tool to execute Python code in your chain of thought. The code will not be shown to the user. This tool should be used for internal reasoning, but not for code that is intended to be visible to the user (e.g. when creating plots, tables, or files).\n\n" }}        {{- "When you send a message containing Python code to python, it will be executed in a stateful Jupyter notebook environment. python will respond with the output of the execution or time out after 120.0 seconds. The drive at '/mnt/data' can be used to save and persist user files. Internet access for this session is UNKNOWN. Depends on the cluster.\n\n" }}    {%- endif -%}{%- endmacro -%}{#- System Message Construction ============================================ #}{%- macro build_system_message() -%}    {%- if model_identity is not defined %}        {%- set model_identity = "You are ChatGPT, a large language model trained by OpenAI." %}    {%- endif %}    {{- model_identity + "\n" }}    {{- "Knowledge cutoff: 2024-06\n" }}    {{- "Current date: " + strftime_now("%Y-%m-%d") + "\n\n" }}    {%- if reasoning_effort is not defined %}        {%- set reasoning_effort = "medium" %}    {%- endif %}    {{- "Reasoning: " + reasoning_effort + "\n\n" }}    {%- if builtin_tools %}        {{- "# Tools\n\n" }}        {%- set available_builtin_tools = namespace(browser=false, python=false) %}        {%- for tool in builtin_tools %}            {%- if tool == "browser" %}                {%- set available_builtin_tools.browser = true %}            {%- elif tool == "python" %}                {%- set available_builtin_tools.python = true %}            {%- endif %}        {%- endfor %}        {{- render_builtin_tools(available_builtin_tools.browser, available_builtin_tools.python) }}    {%- endif -%}    {{- "# Valid channels: analysis, commentary, final. Channel must be included for every message." }}    {%- if tools -%}        {{- "\nCalls to these tools must go to the commentary channel: 'functions'." }}    {%- endif -%}{%- endmacro -%}{#- Main Template Logic ================================================= #}{#- Set defaults #}{#- Render system message #}{{- "<|start|>system<|message|>" }}{{- build_system_message() }}{{- "<|end|>" }}{#- Extract developer message #}{%- if messages[0].role == "developer" or messages[0].role == "system" %}    {%- set developer_message = messages[0].content %}    {%- set loop_messages = messages[1:] %}{%- else %}    {%- set developer_message = "" %}    {%- set loop_messages = messages %}{%- endif %}{#- Render developer message #}{%- if developer_message or tools %}    {{- "<|start|>developer<|message|>" }}    {%- if developer_message %}        {{- "# Instructions\n\n" }}        {{- developer_message }}        {{- "\n\n" }}    {%- endif %}    {%- if tools -%}        {{- "# Tools\n\n" }}        {{- render_tool_namespace("functions", tools) }}    {%- endif -%}    {{- "<|end|>" }}{%- endif %}{#- Render messages #}{%- set last_tool_call = namespace(name=none) %}{%- for message in loop_messages -%}    {#- At this point only assistant/user/tool messages should remain #}    {%- if message.role == 'assistant' -%}        {#- Checks to ensure the messages are being passed in the format we expect #}        {%- if "content" in message %}            {%- if "<|channel|>analysis<|message|>" in message.content or "<|channel|>final<|message|>" in message.content %}                {{- raise_exception("You have passed a message containing <|channel|> tags in the content field. Instead of doing this, you should pass analysis messages (the string between '<|message|>' and '<|end|>') in the 'thinking' field, and final messages (the string between '<|message|>' and '<|end|>') in the 'content' field.") }}            {%- endif %}        {%- endif %}        {%- if "thinking" in message %}            {%- if "<|channel|>analysis<|message|>" in message.thinking or "<|channel|>final<|message|>" in message.thinking %}                {{- raise_exception("You have passed a message containing <|channel|> tags in the thinking field. Instead of doing this, you should pass analysis messages (the string between '<|message|>' and '<|end|>') in the 'thinking' field, and final messages (the string between '<|message|>' and '<|end|>') in the 'content' field.") }}            {%- endif %}        {%- endif %}        {%- if "tool_calls" in message %}            {#- We need very careful handling here - we want to drop the tool call analysis message if the model #}            {#- has output a later <|final|> message, but otherwise we want to retain it. This is the only case #}            {#- when we render CoT/analysis messages in inference. #}            {%- set future_final_message = namespace(found=false) %}            {%- for future_message in loop_messages[loop.index:] %}                {%- if future_message.role == 'assistant' and "tool_calls" not in future_message %}                    {%- set future_final_message.found = true %}                {%- endif %}            {%- endfor %}            {#- We assume max 1 tool call per message, and so we infer the tool call name #}            {#- in "tool" messages from the most recent assistant tool call name #}            {%- set tool_call = message.tool_calls[0] %}            {%- if tool_call.function %}                {%- set tool_call = tool_call.function %}            {%- endif %}            {%- if message.content and message.thinking %}                {{- raise_exception("Cannot pass both content and thinking in an assistant message with tool calls! Put the analysis message in one or the other, but not both.") }}            {%- elif message.content and not future_final_message.found %}                {{- "<|start|>assistant<|channel|>analysis<|message|>" + message.content + "<|end|>" }}            {%- elif message.thinking and not future_final_message.found %}                {{- "<|start|>assistant<|channel|>analysis<|message|>" + message.thinking + "<|end|>" }}            {%- endif %}            {{- "<|start|>assistant to=" }}            {{- "functions." + tool_call.name + "<|channel|>commentary " }}            {{- (tool_call.content_type if tool_call.content_type is defined else "json") + "<|message|>" }}            {{- tool_call.arguments|tojson }}            {{- "<|call|>" }}            {%- set last_tool_call.name = tool_call.name %}        {%- elif loop.last and not add_generation_prompt %}            {#- Only render the CoT if the final turn is an assistant turn and add_generation_prompt is false #}            {#- This is a situation that should only occur in training, never in inference. #}            {%- if "thinking" in message %}                {{- "<|start|>assistant<|channel|>analysis<|message|>" + message.thinking + "<|end|>" }}            {%- endif %}            {#- <|return|> indicates the end of generation, but <|end|> does not #}            {#- <|return|> should never be an input to the model, but we include it as the final token #}            {#- when training, so the model learns to emit it. #}            {{- "<|start|>assistant<|channel|>final<|message|>" + message.content + "<|return|>" }}        {%- else %}            {#- CoT is dropped during all previous turns, so we never render it for inference #}            {{- "<|start|>assistant<|channel|>final<|message|>" + message.content + "<|end|>" }}            {%- set last_tool_call.name = none %}        {%- endif %}    {%- elif message.role == 'tool' -%}        {%- if last_tool_call.name is none %}            {{- raise_exception("Message has tool role, but there was no previous assistant message with a tool call!") }}        {%- endif %}        {{- "<|start|>functions." + last_tool_call.name }}        {{- " to=assistant<|channel|>commentary<|message|>" + message.content|tojson + "<|end|>" }}    {%- elif message.role == 'user' -%}        {{- "<|start|>user<|message|>" + message.content + "<|end|>" }}    {%- endif -%}{%- endfor -%}{#- Generation prompt #}{%- if add_generation_prompt -%}<|start|>assistant{%- endif -%}
"""

# 2. Jinja2 환경(Environment)을 설정합니다.
# lstrip_blocks와 trim_blocks는 템플릿의 불필요한 공백을 제거해 줍니다.
env = Environment(lstrip_blocks=True, trim_blocks=True)

# 템플릿 내에서 사용하는 strftime_now 함수를 파이썬 코드로 정의하고,
# Jinja2 환경의 전역 변수로 등록합니다.
def strftime_now(fmt):
    """현재 시간을 지정된 포맷의 문자열로 반환합니다."""
    return datetime.now().strftime(fmt)

env.globals['strftime_now'] = strftime_now

# 3. 템플릿을 로드합니다.
template = env.from_string(template_string)


# 4. 템플릿 렌더링에 사용할 데이터(컨텍스트)를 정의합니다.
# 이 데이터는 템플릿의 모든 분기(tool 사용, role별 메시지 등)를 테스트할 수 있도록 구성합니다.
render_context = {
    # -- 템플릿 주석에서 언급된 추가 kwargs --
    "model_identity": "당신은 사용자에게 도움이 되는 AI 어시스턴트, '하모니'입니다.",
    "reasoning_effort": "high",
    "builtin_tools": ["browser", "python"],
    
    # -- 일반적인 입력값 --
    "tools": [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "특정 위치의 현재 날씨를 가져옵니다.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "도시와 주(state), 예: San Francisco, CA"
                        },
                        "unit": {
                            "type": "string",
                            "enum": ["celsius", "fahrenheit"],
                            "default": "celsius"
                        }
                    },
                    "required": ["location"]
                }
            }
        }
    ],
    "messages": [
        # 템플릿은 messages[0]가 'developer' role일 경우 특별 처리하므로,
        # developer 지침을 추가해 봅니다.
        {
            "role": "developer",
            "content": "모든 답변은 한국어로 해야 합니다. 날씨를 알려줄 때는 반드시 이모지를 사용하세요."
        },
        {
            "role": "user",
            "content": "샌프란시스코의 날씨는 어떤가요?"
        },
        # Assistant가 tool_calls를 사용하고, 생각을 정리하는 'thinking' 필드를 사용하는 경우
        {
            "role": "assistant",
            "thinking": "사용자가 샌프란시스코의 날씨를 물어봤으니 get_weather 도구를 사용해야겠다. unit은 기본값인 celsius로 호출하자.",
            "tool_calls": [
                {
                    "function": {
                        "name": "get_weather",
                        "arguments": json.dumps({"location": "San Francisco, CA"})
                    }
                }
            ]
        },
        # 이전 assistant의 tool_calls에 대한 응답
        {
            "role": "tool",
            "content": json.dumps({"temperature": "14", "unit": "celsius", "description": "구름 많음"})
        },
        # tool 응답을 바탕으로 최종 답변을 하는 assistant
        {
            "role": "assistant",
            "content": "샌프란시스코의 현재 날씨는 14°C이며, 구름이 많은 날씨입니다. ☁️"
        }
    ],
    # 다음 assistant 응답을 생성하도록 프롬프트를 추가합니다.
    "add_generation_prompt": True
}


# 5. 템플릿을 렌더링하고 결과를 출력합니다.
try:
    rendered_output = template.render(render_context)
    print("--- 렌더링된 프롬프트 결과 ---")
    print(rendered_output)
except Exception as e:
    print(f"템플릿 렌더링 중 오류 발생: {e}")
