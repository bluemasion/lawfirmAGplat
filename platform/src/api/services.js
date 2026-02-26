// ========================================
// API 接口层 — 当前返回 mock data
// 切换真实后端时，只需将 mock 调用改为 fetch()
// ========================================

import * as mock from './mock';

/** 获取 Dashboard KPI 指标 */
export const getDashboardMetrics = () => Promise.resolve(mock.dashboardMetrics);

/** 获取算力利用率数据 */
export const getUtilizationData = () => Promise.resolve(mock.utilizationData);

/** 获取模型实例列表 */
export const getModelInstances = () => Promise.resolve(mock.modelInstances);

/** 获取硬件资源指标 */
export const getResourceMetrics = () => Promise.resolve(mock.resourceMetrics);

/** 获取在线会话列表 */
export const getActiveSessions = () => Promise.resolve(mock.activeSessions);

/** 获取 NER 脱敏规则 */
export const getNerRules = () => Promise.resolve(mock.defaultNerRules);

/** 执行 NER 脱敏（当前为本地模拟，后续接 Legal-BERT 服务） */
export const runNerMask = (text, rules) => {
    let result = text;
    if (rules.find(r => r.id === 'per')?.enabled) result = result.replace(/张三/g, '[姓名_ID1]').replace(/李四/g, '[姓名_ID2]');
    if (rules.find(r => r.id === 'org')?.enabled) result = result.replace(/深圳市腾讯计算机系统有限公司/g, '[机构_ID_A]');
    if (rules.find(r => r.id === 'amt')?.enabled) result = result.replace(/500万元/g, '[金额_MASKED]');
    return Promise.resolve(result);
};

/** 获取 Agent 应用列表 */
export const getAgentApps = () => Promise.resolve(mock.agentApps);

/** 执行利冲搜索（当前为模拟，后续接知识图谱+实体链接服务） */
export const searchConflict = (query) => {
    return new Promise((resolve) => {
        setTimeout(() => resolve(mock.conflictMockResult), 1200);
    });
};

/** 获取底稿文件列表 */
export const getSecuritiesFiles = () => Promise.resolve(mock.securitiesFiles);

/** 终止用户会话 */
export const terminateSession = (sessionId) => {
    // TODO: 接入真实后端 DELETE /api/sessions/:id
    return Promise.resolve({ success: true });
};
