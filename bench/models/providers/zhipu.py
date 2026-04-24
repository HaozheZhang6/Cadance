"""Zhipu AI (智谱) GLM adapter — glm-4 / glm-4.5 / glm-4.6 families.

OpenAI-compatible API at https://open.bigmodel.cn/api/paas/v4. Requires
ZHIPU_API_KEY. glm-4v* / glm-4.5-v support images; text models do not
(adapter unconditionally forwards images — provider will reject if unsupported).
"""

from __future__ import annotations

from bench.models.registry import register

from ._openai_compat import OpenAICompatAdapter


@register(
    # GLM-4
    "glm-4",
    "glm-4-plus",
    "glm-4-long",
    "glm-4-air",
    "glm-4-airx",
    "glm-4-flash",
    "glm-4-flashx",
    "glm-4v",
    "glm-4v-plus",
    "glm-4v-flash",
    # GLM-4.5
    "glm-4.5",
    "glm-4.5-air",
    "glm-4.5-x",
    "glm-4.5-flash",
    "glm-4.5-v",
    # GLM-4.6
    "glm-4.6",
)
class ZhipuAdapter(OpenAICompatAdapter):
    base_url = "https://open.bigmodel.cn/api/paas/v4"
    env_key = "ZHIPU_API_KEY"
    supports_images = True
