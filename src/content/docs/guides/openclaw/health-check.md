---
title: 如何確認 OpenClaw 已正常啟動
description: 教普通用家在完成安裝後，用幾個簡單檢查確認 OpenClaw 是否已正常啟動：版本號、gateway 狀態、控制畫面與 openclaw
  doctor。
type: guide
topic: openclaw-health-check
status: publish_ready
reviewedAt: '2026-03-19T11:15:00+00:00'
related:
- guides/openclaw/mac-install
slug: guides/openclaw/health-check
knowledge_id: knowledge_seed_openclaw_health_check_0001
publication_state: publish_ready
route_version: route_v2
access_level: free
projection_version: g2g3-integ-w1
site_type_projection: guide
target_site_type: guide
target_chinese_template: guide
required_reader_sections: &id001
- 先看結論
- 適合誰
- 開始前準備
- 步驟
- 預期結果
- 常見錯誤
- 下一步
forbidden_leaks: &id002
- operator-only fields
- missing prerequisites
- contributor-only steps in public guide
target_template: guide
preview_publish_boundary:
  private_preview_candidate: &id003
    previewable: false
    go_live: false
    nav_search_visible: false
    approval_required: false
  public_candidate: &id004
    previewable: true
    go_live: false
    nav_search_visible: true
    approval_required: false
  preview_deployment_candidate: &id005
    previewable: true
    go_live: false
    nav_search_visible: true
    approval_required: false
  publish_ready_content: &id006
    previewable: true
    go_live: true
    nav_search_visible: true
    approval_required: false
  boundary_public_candidate_clean: true
  withheld_reason: null
  can_auto_live: false
nav_hidden: false
search_hidden: false
boundary_public_candidate_clean: true
public_site_projection:
  projection_version: g2g3-integ-w1
  publication_state: publish_ready
  site_type_projection: guide
  target_site_type: guide
  target_chinese_template: guide
  required_reader_sections: *id001
  forbidden_leaks: *id002
  preview_publish_boundary:
    private_preview_candidate: *id003
    public_candidate: *id004
    preview_deployment_candidate: *id005
    publish_ready_content: *id006
    boundary_public_candidate_clean: true
    withheld_reason: null
    can_auto_live: false
pagefind: true
sidebar:
  hidden: false
---

# 如何確認 OpenClaw 已正常啟動

## 先看結論
完成安裝之後，你應該可以用 `openclaw --version` 看到版本號，用 `openclaw gateway status` 看到 gateway 狀態，再用 `openclaw dashboard` 打開控制畫面；如果想再核對一次設定是否通順，可以再跑 `openclaw doctor`。這篇只教你做普通用家真係會用到的啟動檢查。

## 步驟
步驟 1：先確認 OpenClaw CLI 仍然可用。
```bash
openclaw --version
```
做完後你應該會見到版本號，而唔係 `command not found`。

步驟 2：檢查 gateway 狀態。
```bash
openclaw gateway status
```
做完後你應該會見到 gateway healthy 或可連線狀態。

步驟 3：打開控制畫面。
```bash
openclaw dashboard
```
做完後你應該會見到 Control UI 打開。

步驟 4：如果你想再核對一次設定是否完整，可以跑 doctor。
```bash
openclaw doctor
```
做完後你應該會見到主要設定冇阻塞錯誤。

## 驗證方式
版本檢查成功時，`openclaw --version` 會印出版本號。

gateway 檢查成功時，`openclaw gateway status` 會顯示 healthy 或可連線狀態。

控制畫面檢查成功時，`openclaw dashboard` 會打開 Control UI。

`openclaw doctor` 成功時，應指出主要設定冇阻塞錯誤。

## 常見錯誤
E1 對應步驟 1：如果 `openclaw --version` 出現 `command not found`，多數係安裝未完成，或者 shell PATH 未更新。

E2 對應步驟 2：如果 `openclaw gateway status` 顯示 gateway 未 healthy，先重跑 `openclaw onboard --install-daemon`，再檢查一次。

E3 對應步驟 3：如果 `openclaw dashboard` 無反應或打唔開，先確認 gateway 狀態已正常，再重試一次。

E4 對應步驟 4：如果 `openclaw doctor` 指出設定有問題，先按提示修正，再回頭檢查 gateway 狀態與控制畫面。

E5 通用求助：如果上面都搵唔到你的錯誤，可以直接複製錯誤文字，或者截圖問 AI，請它幫你判斷下一步應先檢查 gateway、dashboard、doctor，定係重跑 onboarding。

## 下一步
如果上面檢查都成功，你可以回到 OpenClaw 繼續使用，或者重看安裝指南核對有冇漏做首次設定。

## 更新與覆核
- 最近檢查日期：2026-03-19。
- 如果 gateway 指令、dashboard 開啟方式、或者本機 health 檢查方式有變，這篇會再更新。
- 如果你照住做仍然未能確認 OpenClaw 已啟動，先看上面的常見錯誤，再留意官方文件有冇更新。

## Source Trace
- source_type: private_content_batch
- source_value: knowledge/content_batches/guide_seed_openclaw_health_check_batch/specs.json#openclaw-health-check
- content_type: guide
- topic: openclaw-health-check
- task_id: T20260319101500002001
- attempt_id: A20260319101500002001
