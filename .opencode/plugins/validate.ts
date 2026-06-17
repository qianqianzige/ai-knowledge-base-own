import type { Plugin } from "@opencode-ai/plugin"

export const ValidateHook: Plugin = async ({ $ }) => {
  return {
    "tool.execute.after": async (input) => {
      const tool = input.tool
      const filePath = input.args?.file_path ?? input.args?.filePath ?? ""

      // 只对 knowledge/articles/ 下的 JSON 文件触发
      if (
        (tool === "write" || tool === "edit") &&
        typeof filePath === "string" &&
        filePath.includes("knowledge/articles/") &&
        filePath.endsWith(".json")
      ) {
        try {
          // 调用 Python 校验脚本
          await $`python3 hooks/validate_json.py ${filePath}`.nothrow()
        } catch {
          // 吞掉异常，避免阻塞 OpenCode
        }
      }
    },
  }
}
