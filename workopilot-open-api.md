# 数字员工开放 API 接口文档

> 来源：http://docs.workopilot.com/api/digital-employee/open-api.html

## 1. 概述

本文档描述数字员工对外开放接口，供第三方系统通过 `API-KEY` 调用数字员工能力。

对话接口同时支持：

- `stream=true`：SSE 流式返回
- `stream=false`：普通 JSON 返回

**接口根路径：**

```
/api/ai/open
```

**通用请求头：**

```http
API-KEY: your-api-key
Content-Type: application/json
```

**说明：**

- `robotId` 必须属于当前 `API-KEY` 对应租户
- `userId` 是第三方系统中的用户标识，系统内部会映射为会话归属 `VisitorId`
- `ctx.*` 仅通过 query string 传递，例如 `?ctx.source=crm&ctx.bizOrderId=SO20260416`

**上下文优先级 — 系统保留字段最后覆盖：**

- `external_user_id / externalUserId / user_id / userId`
- `external_user_name / externalUserName / user_name / userName`

---

## 2. 获取数字员工资料

### 地址

```http
GET /api/ai/open/robot/profile
```

### 功能

按 `robotId` 获取当前租户下数字员工基础资料。

### 请求参数

| 参数名 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| `robotId` | query | long | 是 | 数字员工主键 ID |
| `baseUrl` | query | string | 否 | 菜单直达链接基础地址，例如 `https://agent.workopilot.com`。不传时后端尝试按当前请求域名生成 |

### 请求示例

```http
GET /api/ai/open/robot/profile?robotId=2038862861584961500&baseUrl=https://agent.workopilot.com
API-KEY: your-api-key
```

### 返回示例

```json
{
  "code": 200,
  "msg": null,
  "data": {
    "id": 2038862861584961500,
    "robotCode": "cxy001",
    "robotName": "促销员",
    "avatarUrl": "https://example.com/avatar.png",
    "welcomeMessage": "您好，我可以帮您整理报价与产品信息。",
    "businessLine": "pharma",
    "isActive": 1,
    "appMenus": [
      {
        "id": 2041024000000000001,
        "menuType": "internal",
        "displayMode": "card",
        "menuKey": "quote-history",
        "title": "报价记录",
        "icon": "lucide:file-text",
        "routePath": "/app/quote-history",
        "componentPath": "quote-history",
        "iframeUrl": null,
        "directUrl": "https://agent.workopilot.com/embed/chat/2038862861584961500?token=xxx&externalUserId={userId}&externalUserName={userName}&menuKey=quote-history",
        "sort": 10,
        "isEnabled": true
      }
    ]
  },
  "total": 0,
  "rows": null
}
```

### 返回字段补充

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `appMenus` | array | 当前数字员工已启用的应用菜单。仅当员工启用应用入口时返回菜单数据；未启用或无菜单时返回空数组 |

---

## 2.1 获取当前租户启用的数字员工列表

### 地址

```http
GET /api/ai/open/robots
```

### 功能

返回当前 `API-KEY` 所属租户下所有启用中的数字员工，用于第三方系统先展示可用员工，再选择 `robotId` 发起会话。

### 请求参数

| 参数名 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| `baseUrl` | query | string | 否 | 分享链接基础地址，例如 `https://agent.workopilot.com`。不传时后端尝试按当前请求域名生成 |

### 请求示例

```http
GET /api/ai/open/robots?baseUrl=https://agent.workopilot.com
API-KEY: your-api-key
```

### 返回字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `robotId` | long | 数字员工 ID |
| `robotCode` | string | 数字员工编码 |
| `robotName` | string | 数字员工名称 |
| `avatarUrl` | string | 头像地址 |
| `description` | string | 说明 |
| `intro` | string | 简介，优先取员工备注，备注为空时取欢迎语 |
| `enableShare` | bool | 是否已启用分享/iframe 嵌入 |
| `shareUrl` | string | 分享链接；未启用分享时为空 |
| `appMenus` | array | 当前数字员工已启用的应用菜单。仅当员工启用应用入口时返回菜单数据；未启用或无菜单时返回空数组 |

### appMenus 字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | long | 菜单 ID |
| `menuType` | string | 菜单类型：`internal` 内置页面，`iframe` 外部 iframe 页面 |
| `displayMode` | string | 展示方式，例如 `card`、`fullscreen` |
| `menuKey` | string | 菜单唯一键。第三方需要直达某个菜单时，应使用该值作为跳转标识 |
| `title` | string | 菜单名称 |
| `icon` | string | 菜单图标标识，例如 `lucide:file-text`。这是展示建议，第三方没有对应图标库时可使用默认图标、首字或自行映射 |
| `routePath` | string | 内部路由路径，仅供展示或调试参考 |
| `componentPath` | string | 内置组件路径，`menuType=internal` 时可能存在 |
| `iframeUrl` | string | iframe 地址，`menuType=iframe` 时可能存在 |
| `directUrl` | string | 菜单直达分享链接。格式为 `https://xxx/embed/chat/{robotId}?token=xxx&externalUserId={userId}&externalUserName={userName}&menuKey={menuKey}`；当员工未启用分享或缺少 token 时为空 |
| `sort` | int | 排序值 |
| `isEnabled` | bool | 是否启用。开放接口只返回已启用菜单，通常为 `true` |

### 返回示例

```json
{
  "code": 200,
  "msg": null,
  "data": null,
  "total": 2,
  "rows": [
    {
      "robotId": 2038862861584961500,
      "robotCode": "cxy001",
      "robotName": "促销员",
      "avatarUrl": "https://example.com/avatar.png",
      "description": "负责报价、商品推荐和客户沟通",
      "intro": "面向销售场景的数字员工",
      "enableShare": true,
      "shareUrl": "https://agent.workopilot.com/embed/chat/2038862861584961500?token=xxx&externalUserId={userId}&externalUserName={userName}",
      "appMenus": [
        {
          "id": 2041024000000000001,
          "menuType": "internal",
          "displayMode": "card",
          "menuKey": "quote-history",
          "title": "报价记录",
          "icon": "lucide:file-text",
          "routePath": "/app/quote-history",
          "componentPath": "quote-history",
          "iframeUrl": null,
          "directUrl": "https://agent.workopilot.com/embed/chat/2038862861584961500?token=xxx&externalUserId={userId}&externalUserName={userName}&menuKey=quote-history",
          "sort": 10,
          "isEnabled": true
        },
        {
          "id": 2041024000000000002,
          "menuType": "iframe",
          "displayMode": "fullscreen",
          "menuKey": "external-report",
          "title": "外部报表",
          "icon": "lucide:chart-no-axes-combined",
          "routePath": "",
          "componentPath": null,
          "iframeUrl": "https://example.com/report",
          "directUrl": "https://agent.workopilot.com/embed/chat/2038862861584961500?token=xxx&externalUserId={userId}&externalUserName={userName}&menuKey=external-report",
          "sort": 20,
          "isEnabled": true
        }
      ]
    }
  ]
}
```

---

## 3. 创建新 Session

### 地址

```http
POST /api/ai/open/chat/session
```

### 功能

创建或续用某个用户在某个数字员工下的会话。

### 请求体

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `RobotId` | long | 是 | 数字员工 ID |
| `UserId` | string | 是 | 第三方系统用户 ID |
| `UserName` | string | 否 | 第三方系统用户名称 |
| `SessionId` | string | 否 | 传入则优先尝试续用该会话 |
| `ContextData` | object | 否 | 业务上下文 |

### 请求示例

```json
{
  "robotId": 2038862861584961500,
  "userId": "u_10001",
  "userName": "王安康",
  "sessionId": "",
  "contextData": {
    "channel": "crm",
    "region": "hk"
  }
}
```

### 返回示例

```json
{
  "code": 200,
  "msg": null,
  "data": {
    "sessionId": "af0d84f7f0f44e90a8f463f8d54fe218",
    "robotName": "促销员",
    "avatarUrl": "https://example.com/avatar.png",
    "welcomeMessage": "您好，我可以帮您整理报价与产品信息。",
    "enableAsr": true,
    "enableTts": true
  },
  "total": 0,
  "rows": null
}
```

---

## 4. 获取 Session 列表

### 地址

```http
GET /api/ai/open/chat/sessions
```

### 功能

获取某个用户在指定数字员工下的会话列表。

### 请求参数

| 参数名 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| `robotId` | query | long | 是 | 数字员工 ID |
| `userId` | query | string | 是 | 第三方系统用户 ID |
| `pageNum` | query | int | 否 | 页码，默认 1 |
| `pageSize` | query | int | 否 | 每页条数，默认按系统分页配置 |
| `sessionTitle` | query | string | 否 | 会话标题模糊搜索 |

### 请求示例

```http
GET /api/ai/open/chat/sessions?robotId=2038862861584961500&userId=u_10001&pageNum=1&pageSize=20
API-KEY: your-api-key
```

### 返回示例

```json
{
  "code": 200,
  "msg": null,
  "data": null,
  "total": 2,
  "rows": [
    {
      "id": 2039020000000000001,
      "sessionId": "af0d84f7f0f44e90a8f463f8d54fe218",
      "robotId": 2038862861584961500,
      "robotCode": "cxy001",
      "userId": null,
      "visitorId": "openapi:12:u_10001",
      "userName": null,
      "sessionTitle": "帮我挑一批牙科诊所药品",
      "isActive": 1,
      "msgCount": 6,
      "lastMsgAt": "2026-04-16 18:22:15",
      "embedSource": null,
      "createTime": "2026-04-16 18:18:01",
      "updateTime": "2026-04-16 18:22:15"
    }
  ]
}
```

---

## 5. 获取某个 Session 的对话记录

### 地址

```http
GET /api/ai/open/chat/history
```

### 功能

获取指定会话的历史消息，仅允许读取当前 `userId` 自己的会话。

### 请求参数

| 参数名 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| `robotId` | query | long | 是 | 数字员工 ID |
| `userId` | query | string | 是 | 第三方系统用户 ID |
| `sessionId` | query | string | 是 | 会话 ID |
| `pageNum` | query | int | 否 | 页码 |
| `pageSize` | query | int | 否 | 每页条数 |

### 请求示例

```http
GET /api/ai/open/chat/history?robotId=2038862861584961500&userId=u_10001&sessionId=af0d84f7f0f44e90a8f463f8d54fe218&pageNum=1&pageSize=50
API-KEY: your-api-key
```

### 返回示例

```json
{
  "code": 200,
  "msg": null,
  "data": null,
  "total": 2,
  "rows": [
    {
      "id": 2039020000000000101,
      "sessionId": "af0d84f7f0f44e90a8f463f8d54fe218",
      "robotId": 2038862861584961500,
      "role": "user",
      "content": "帮我推荐三种牙科诊所常用药品",
      "audioUrl": null,
      "attachments": null,
      "cardData": null,
      "skillCode": null,
      "toolCalls": null,
      "toolResult": null,
      "inputTokens": null,
      "outputTokens": null,
      "msgStatus": "SUCCESS",
      "errorMsg": null,
      "seq": 1,
      "createTime": "2026-04-16 18:18:01"
    },
    {
      "id": 2039020000000000102,
      "sessionId": "af0d84f7f0f44e90a8f463f8d54fe218",
      "robotId": 2038862861584961500,
      "role": "assistant",
      "content": "可以优先考虑以下三种产品……",
      "audioUrl": null,
      "attachments": null,
      "cardData": "{\"title\":\"已生成产品筛选结果\"}",
      "skillCode": "pharma_sku_filter",
      "toolCalls": "agent_tool_activated",
      "toolResult": null,
      "inputTokens": null,
      "outputTokens": null,
      "msgStatus": "SUCCESS",
      "errorMsg": null,
      "seq": 2,
      "createTime": "2026-04-16 18:18:04"
    }
  ]
}
```

---

## 6. 删除某个 Session

### 地址

```http
DELETE /api/ai/open/chat/session/{sessionId}
```

### 功能

删除指定会话，仅允许删除当前 `userId` 自己的会话。

### 请求参数

| 参数名 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| `sessionId` | path | string | 是 | 会话 ID |
| `robotId` | query | long | 是 | 数字员工 ID |
| `userId` | query | string | 是 | 第三方系统用户 ID |

### 请求示例

```http
DELETE /api/ai/open/chat/session/af0d84f7f0f44e90a8f463f8d54fe218?robotId=2038862861584961500&userId=u_10001
API-KEY: your-api-key
```

### 返回示例

```json
{
  "code": 200,
  "msg": "会话已删除",
  "data": true,
  "total": 0,
  "rows": null
}
```

---

## 7. 发送对话消息

### 地址

```http
POST /api/ai/open/chat/send
```

### 功能

发送用户消息，支持流式与非流式两种模式。

### 请求体

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `RobotId` | long | 是 | 数字员工 ID |
| `UserId` | string | 是 | 第三方系统用户 ID |
| `UserName` | string | 否 | 第三方系统用户名 |
| `SessionId` | string | 否 | 会话 ID，空则自动新建 |
| `Content` | string | 否 | 用户输入内容，和 `Message` 二选一 |
| `Message` | string | 否 | 用户输入内容，和 `Content` 二选一 |
| `Files` | array[string] | 否 | 文件 URL 列表，优先于 `Attachments` |
| `Attachments` | array[string] | 否 | 附件 URL 列表 |
| `ContextData` | object | 否 | 业务上下文 |
| `Stream` | bool | 否 | 是否流式，默认 `true` |

### 支持的 ctx.* 参数

发送接口支持在 query 上传递业务上下文：

```http
POST /api/ai/open/chat/send?ctx.source=crm&ctx.bizOrderId=SO20260416
```

### 非流式请求示例

```json
{
  "robotId": 2038862861584961500,
  "userId": "u_10001",
  "userName": "王安康",
  "sessionId": "",
  "content": "帮我推荐三种牙科诊所常用药品，并说明适用场景",
  "files": [],
  "contextData": {
    "channel": "crm"
  },
  "stream": false
}
```

### 非流式返回示例

```json
{
  "code": 200,
  "msg": null,
  "data": {
    "sessionId": "af0d84f7f0f44e90a8f463f8d54fe218",
    "requestId": null,
    "message": "可以优先考虑以下三种产品……",
    "cardData": "{\"title\":\"已生成产品筛选结果\"}",
    "attachments": []
  },
  "total": 0,
  "rows": null
}
```

### 流式请求说明

当 `Stream=true` 时，接口返回：

```http
Content-Type: text/event-stream
```

SSE 事件格式主要事件包括：

| 事件 | 说明 |
| --- | --- |
| `text` | 增量文本 |
| `tool_call` | 工具调用 |
| `tool_result` | 工具返回 |
| `frontend_command` | 前端动作 |
| `card` | 卡片事件 |
| `done` | 对话完成 |
| `error` | 执行异常 |

### 流式返回示例

```
event: text
cfdata: {"text":"可以优先考虑以下三种产品"}
data: {"text":"可以优先考虑以下三种产品"}

event: card
cfdata: {"title":"已生成产品筛选结果","skillCode":"pharma_sku_filter"}
data: {"title":"已生成产品筛选结果","skillCode":"pharma_sku_filter"}

event: done
cfdata: {"messageId":"2039020000000000102","sessionId":"af0d84f7f0f44e90a8f463f8d54fe218"}
data: {"messageId":"2039020000000000102","sessionId":"af0d84f7f0f44e90a8f463f8d54fe218"}
```

---

## 8. 错误响应示例

### API Key 缺失

```json
{
  "code": 401,
  "msg": "API Key missing"
}
```

### API Key 无权限

```json
{
  "code": 403,
  "msg": "Invalid API Key or Permission Denied"
}
```

### 数字员工不属于当前租户

```json
{
  "code": 500,
  "msg": "数字员工不存在或不属于当前租户"
}
```

### 当前会话不属于该用户

```json
{
  "code": 500,
  "msg": "未找到当前用户的会话"
}
```

### 流式错误事件

```
event: error
cfdata: {"message":"消息内容不能为空"}
data: {"message":"消息内容不能为空"}
```

---

## 9. 字段说明补充

### robotId

- 数字员工主键 ID
- 必须属于当前 `API-KEY` 对应租户

### userId

- 第三方业务系统用户唯一标识
- 系统内部会转换为 `VisitorId`
- 当前实现规则：`openapi:{apiKeyId}:{userId}`

### sessionId

- 对话会话主键
- 创建时可不传
- 发送对话时不传则自动新建
- 查询历史、删除会话时必须传且必须属于当前用户

### ctx.*

- 通过 query string 传入
- 适用于业务标识、来源渠道、单据号等附加上下文
- 示例：`?ctx.source=crm&ctx.bizOrderId=SO20260416&ctx.company=華達藥業有限公司`
