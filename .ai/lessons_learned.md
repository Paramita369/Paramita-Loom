# Vibe Commander — Lessons Learned

## Run d7936f95 — 2026-03-29
**Tags**: [testing] [security] [hooks] [state] [auth] [backup]
**What went wrong**: 補強了 pre_tool_gate、post_tool_validator、codex_worker、state_manager 備份、auth adapters 共 32 個測試。state_manager.save_state() 新增備份邏輯（先備份舊檔再原子寫入）。
**Root cause**: 最關鍵元件（唯一寫入閘道、安全 hook、auth）缺乏直接測試，形成「最重要的元件最少測試」反模式。
**Prevention**: 每個新元件實作後必須立即補充測試。P0 安全相關元件需在計畫階段即列入 test coverage plan，不得延後。
