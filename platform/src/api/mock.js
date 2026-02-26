// ========================================
// 集中 Mock 数据 — 后续切换真实后端只需改 services.js
// ========================================

export const dashboardMetrics = [
    { label: '活跃算力节点', value: '3 Nodes', trend: '+2 nodes' },
    { label: 'Token 吞吐流量', value: '1,284', unit: 'k', trend: '+14.2%' },
    { label: '本地脱敏调用', value: '12,842', trend: '+826' },
    { label: '平均检索延时', value: '0.42', unit: 'sec', trend: '-0.05s' },
];

export const utilizationData = [40, 60, 45, 90, 85, 70, 65, 50, 45, 80, 75, 95];

export const modelInstances = [
    { id: 'local', name: 'Legal-Private-v1', provider: '本地部署', status: 'Running', latency: '12ms' },
    { id: 'qwen', name: 'Qwen-Max-0224', provider: '阿里云 VPC', status: 'Ready', latency: '42ms' },
    { id: 'deepseek', name: 'DeepSeek-V3-Pro', provider: '混合云专线', status: 'Ready', latency: '38ms' },
];

export const resourceMetrics = [
    { label: 'GPU (Tesla T4)', usage: 42, details: '显存: 7.2 / 16 GB', color: 'emerald' },
    { label: 'CPU (32-Core)', usage: 18, details: '负载: 2.14, 2.12', color: 'blue' },
    { label: '内存 (RAM)', usage: 25, details: '32.1 / 128 GB', color: 'amber' },
    { label: '持久化存储 (SSD)', usage: 64, details: '1.2 / 2.0 TB', color: 'rose' },
];

export const activeSessions = [
    { name: '王大明 (证券合伙人)', activity: '底稿一致性扫描', connected: '22:15:32' },
    { name: '李晓云 (资深律师)', activity: '高保真翻译导出', connected: '22:15:32' },
    { name: '张小杰 (法律助理)', activity: '利冲排查任务', connected: '22:15:32' },
];

export const defaultNerRules = [
    { id: 'per', label: '人名识别脱敏 (Identity)', enabled: true },
    { id: 'org', label: '机构/律所名称 (Org)', enabled: true },
    { id: 'amt', label: '敏感数值模糊 (Financial)', enabled: true },
    { id: 'case', label: '法律案号识别 (CaseID)', enabled: false },
];

export const agentApps = [
    { id: 'securities', title: '证券底稿核查', desc: '企业级 IPO 底稿多维一致性比对、风险扫描及自动归档引擎。', status: '运行中' },
    { id: 'translation', title: '法律高保真翻译', desc: '1:1 格式还原翻译，支持印章排版深度对齐及术语库对齐。', status: '稳定' },
    { id: 'conflict', title: '利冲检索助手', desc: '基于私有化语义模型，实现穿透式别名识别及关联方冲突研判。', status: '稳定' },
    { id: 'bidding', title: '智能投标中心', desc: '自动抓取案管数据及律师履历，智能补全招标文件强制响应项。', status: '在线' },
];

export const conflictMockResult = {
    risk: 'HIGH',
    matches: [
        { name: '腾讯控股', relation: '母公司', status: '历史在办' },
        { name: '腾讯科技', relation: '子公司', status: '当前顾问' },
    ],
};

export const securitiesFiles = [
    '01-核查说明.docx',
    '02-访谈记录.pdf',
    '03-政府官网截图.png',
    '04-危废处理合同.pdf',
    '05-项目台账.xlsx',
];
