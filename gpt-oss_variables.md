분석 및 필수 입력값
코드를 작성하기 전에 템플릿이 요구하는 주요 입력값들을 파악해야 합니다.

messages: 대화 내역 리스트. 각 항목은 role과 content를 가집니다. assistant의 메시지는 tool_calls, thinking 등을 추가로 가질 수 있습니다.

tools: 사용자가 정의하는 도구의 리스트. JSON 스키마 형식으로 함수를 설명합니다.

builtin_tools: ["browser", "python"]과 같이 내장 도구의 이름을 담은 리스트입니다.

model_identity: 모델의 역할을 설명하는 문자열 (예: "You are a helpful assistant.").

reasoning_effort: 모델의 추론 수준을 나타내는 문자열 (예: "high", "medium").

add_generation_prompt: True로 설정하면, 템플릿 끝에 모델의 다음 응답을 유도하는 <|start|>assistant를 추가합니다.
