import { useState, useEffect } from 'react';
import { ArrowLeft, Search as SearchIcon, AlertTriangle, CheckCircle, Loader2, Ban, Building2, FileText, Shield } from 'lucide-react';

// 穿透扫描分步数据
const scanSteps = [
    { label: '精确匹配', desc: '在案管系统中精确检索目标名称...', duration: 600 },
    { label: '别名穿透', desc: '检索工商注册别名、曾用名及英文名...', duration: 800 },
    { label: '关联方图谱', desc: '识别母公司/子公司/关联自然人...', duration: 1000 },
    { label: '历史案件', desc: '匹配历史在办/已结案件记录...', duration: 700 },
    { label: '风险评估', desc: '综合评估利益冲突风险等级...', duration: 500 },
];

// 不同查询的 mock 结果
const mockResults = {
    '腾讯': {
        risk: 'HIGH',
        entity: '腾讯科技(深圳)有限公司',
        aliases: ['腾讯控股', 'Tencent Holdings', '深圳市腾讯计算机系统有限公司'],
        matches: [
            { name: '腾讯控股有限公司', relation: '母公司', status: '历史在办', detail: '2023年并购项目法律顾问', caseNo: '(2023)内案0456号' },
            { name: '腾讯科技(深圳)有限公司', relation: '全资子公司', status: '当前顾问', detail: '2024-2026常年法律顾问', caseNo: '(2024)顾字012号' },
            { name: '微信支付科技有限公司', relation: '关联公司', status: '历史已结', detail: '支付牌照合规审查', caseNo: '(2022)内案0891号' },
        ],
    },
    '华为': {
        risk: 'LOW',
        entity: '华为技术有限公司',
        aliases: ['Huawei Technologies', '华为投资控股'],
        matches: [
            { name: '华为技术有限公司', relation: '直接匹配', status: '历史已结', detail: '2021年专利诉讼代理', caseNo: '(2021)内案0234号' },
        ],
    },
    'default': {
        risk: 'NONE',
        entity: '',
        aliases: [],
        matches: [],
    },
};

function getResult(query) {
    const q = query.trim();
    for (const key of Object.keys(mockResults)) {
        if (key !== 'default' && q.includes(key)) return { ...mockResults[key], searchQuery: q };
    }
    return { ...mockResults['default'], searchQuery: q };
}

export default function ConflictSearch({ onBack }) {
    const [query, setQuery] = useState('');
    const [result, setResult] = useState(null);
    const [scanning, setScanning] = useState(false);
    const [currentStep, setCurrentStep] = useState(-1);
    const [completedSteps, setCompletedSteps] = useState([]);

    const handleScan = () => {
        if (!query.trim() || scanning) return;
        setScanning(true);
        setResult(null);
        setCurrentStep(0);
        setCompletedSteps([]);

        let cumDelay = 0;
        scanSteps.forEach((step, i) => {
            cumDelay += step.duration;
            setTimeout(() => {
                setCurrentStep(i + 1);
                setCompletedSteps(prev => [...prev, i]);
            }, cumDelay);
        });

        setTimeout(() => {
            setScanning(false);
            setCurrentStep(-1);
            setResult(getResult(query));
        }, cumDelay + 400);
    };

    const riskColors = {
        HIGH: { bg: 'bg-red-50', border: 'border-red-300', text: 'text-red-700', badge: 'bg-red-600' },
        LOW: { bg: 'bg-emerald-50', border: 'border-emerald-300', text: 'text-emerald-700', badge: 'bg-emerald-600' },
        NONE: { bg: 'bg-zinc-50', border: 'border-zinc-300', text: 'text-zinc-600', badge: 'bg-zinc-500' },
    };

    return (
        <div className="p-6 space-y-6 animate-in">
            <div className="flex items-center space-x-3 border-b border-zinc-200 pb-4">
                <button onClick={onBack} className="text-zinc-400 hover:text-zinc-700"><ArrowLeft size={16} /></button>
                <div>
                    <h2 className="text-lg font-bold text-zinc-800 uppercase tracking-tight">利冲检索助手</h2>
                    <p className="text-[10px] text-zinc-400 font-bold uppercase tracking-widest">Conflict of Interest — Semantic Deep Scan with Entity Linking</p>
                </div>
            </div>

            <div className="max-w-3xl mx-auto space-y-5">
                {/* 搜索框 */}
                <div className="bg-white border border-zinc-200 rounded-sm p-6 shadow-sm">
                    <label className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest block mb-2">输入检索对象（支持别名、简称穿透）</label>
                    <div className="flex space-x-3">
                        <input type="text" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="例: 腾讯, 华为, 阿里巴巴..."
                            className="flex-1 border border-zinc-300 rounded-sm px-4 py-3 text-sm focus:outline-none focus:border-blue-500 bg-zinc-50 shadow-inner"
                            onKeyDown={(e) => e.key === 'Enter' && handleScan()} disabled={scanning} />
                        <button onClick={handleScan} disabled={scanning}
                            className="px-6 py-3 bg-[#151921] text-white text-xs font-bold rounded-sm uppercase tracking-tight hover:bg-black transition-all flex items-center space-x-2 disabled:opacity-50 shadow-lg">
                            {scanning ? <Loader2 size={14} className="animate-spin" /> : <SearchIcon size={14} />}
                            <span>{scanning ? '扫描中...' : '执行扫描'}</span>
                        </button>
                    </div>
                    <div className="mt-3 flex space-x-2">
                        {['腾讯', '华为', '阿里巴巴'].map(q => (
                            <button key={q} onClick={() => { setQuery(q); }} className="text-[10px] text-zinc-400 hover:text-blue-600 border border-zinc-200 px-2 py-1 rounded-sm hover:border-blue-300 transition">{q}</button>
                        ))}
                    </div>
                </div>

                {/* 扫描进度 */}
                {scanning && (
                    <div className="bg-white border border-zinc-200 rounded-sm p-5 shadow-sm slide-up">
                        <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-3">🔍 穿透扫描进度</p>
                        <div className="space-y-2">
                            {scanSteps.map((step, i) => {
                                const done = completedSteps.includes(i);
                                const active = currentStep === i;
                                return (
                                    <div key={i} className={`flex items-center space-x-3 py-2 px-3 rounded-sm transition-all ${done ? 'bg-emerald-50 border border-emerald-100' : active ? 'bg-blue-50 border border-blue-100' : 'bg-zinc-50 border border-zinc-100'}`}>
                                        {done ? <CheckCircle size={13} className="text-emerald-500 shrink-0" /> :
                                            active ? <Loader2 size={13} className="animate-spin text-blue-500 shrink-0" /> :
                                                <div className="w-3.5 h-3.5 border border-zinc-300 rounded-full shrink-0"></div>}
                                        <div className="flex-1">
                                            <span className={`text-[11px] font-bold ${done ? 'text-emerald-700' : active ? 'text-blue-700' : 'text-zinc-400'}`}>{step.label}</span>
                                            <span className="text-[10px] text-zinc-400 ml-2 italic">{step.desc}</span>
                                        </div>
                                        {done && <span className="text-[9px] text-emerald-500 font-bold">✓</span>}
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}

                {/* 结果展示 */}
                {result && (
                    <div className="space-y-4 slide-up">
                        {/* 风险等级横幅 */}
                        <div className={`${riskColors[result.risk].bg} ${riskColors[result.risk].border} border rounded-sm p-5`}>
                            <div className="flex items-center justify-between mb-3">
                                <div className="flex items-center space-x-2">
                                    {result.risk === 'HIGH' ? <AlertTriangle className="text-red-600" size={20} /> :
                                        result.risk === 'LOW' ? <CheckCircle className="text-emerald-600" size={20} /> :
                                            <CheckCircle className="text-zinc-500" size={20} />}
                                    <span className={`text-sm font-bold uppercase ${riskColors[result.risk].text}`}>
                                        Risk Level: {result.risk}
                                    </span>
                                </div>
                                <span className={`text-[10px] text-white font-bold px-3 py-1 rounded-sm ${riskColors[result.risk].badge}`}>
                                    {result.matches.length} 条关联记录
                                </span>
                            </div>

                            {result.entity && (
                                <div className="mb-3 bg-white/50 rounded-sm p-3 border border-zinc-200/50">
                                    <div className="flex items-center space-x-2 mb-1">
                                        <Building2 size={13} className="text-zinc-600" />
                                        <span className="text-xs font-bold text-zinc-700">识别实体: {result.entity}</span>
                                    </div>
                                    {result.aliases.length > 0 && (
                                        <div className="flex flex-wrap gap-1 mt-1">
                                            {result.aliases.map((a, i) => (
                                                <span key={i} className="text-[9px] bg-zinc-100 text-zinc-500 px-2 py-0.5 rounded-sm border border-zinc-200">{a}</span>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            )}

                            {result.matches.length === 0 && (
                                <p className="text-xs text-zinc-500 italic">未检索到利益冲突关联记录。该客户可以正常承接业务。</p>
                            )}

                            {result.matches.map((m, i) => (
                                <div key={i} className="bg-white/70 rounded-sm p-3 mb-2 border border-zinc-200/50 last:mb-0">
                                    <div className="flex items-center justify-between mb-1">
                                        <div className="flex items-center space-x-2">
                                            <FileText size={12} className="text-zinc-500" />
                                            <span className="text-xs font-bold text-zinc-800">{m.name}</span>
                                            <span className="text-[9px] text-zinc-500 italic">({m.relation})</span>
                                        </div>
                                        <span className={`text-[9px] font-bold uppercase px-2 py-0.5 rounded-sm ${m.status.includes('当前') ? 'bg-red-100 text-red-700 border border-red-200' :
                                                m.status.includes('在办') ? 'bg-amber-100 text-amber-700 border border-amber-200' :
                                                    'bg-zinc-100 text-zinc-600 border border-zinc-200'
                                            }`}>{m.status}</span>
                                    </div>
                                    <div className="flex justify-between text-[10px] text-zinc-500">
                                        <span>{m.detail}</span>
                                        <span className="font-mono">{m.caseNo}</span>
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* 强制回避建议 */}
                        {result.risk === 'HIGH' && (
                            <div className="bg-[#151921] border border-zinc-700 rounded-sm p-5 text-white shadow-2xl">
                                <div className="flex items-center space-x-2 mb-3">
                                    <Ban size={16} className="text-red-500" />
                                    <span className="text-xs font-bold uppercase tracking-wider text-red-400">强制回避建议 (Mandatory Avoidance)</span>
                                </div>
                                <div className="space-y-2 text-[11px] text-zinc-400 leading-relaxed">
                                    <p>基于本所《利益冲突管理办法》第12条，检索目标与本所现有客户存在直接关联关系。建议执行以下措施：</p>
                                    <div className="space-y-1.5 pl-4">
                                        <div className="flex items-center space-x-2"><Shield size={11} className="text-amber-500 shrink-0" /><span>1. 立即通知团队负责合伙人，暂停业务承接流程</span></div>
                                        <div className="flex items-center space-x-2"><Shield size={11} className="text-amber-500 shrink-0" /><span>2. 启动信息隔离墙（Chinese Wall）程序</span></div>
                                        <div className="flex items-center space-x-2"><Shield size={11} className="text-amber-500 shrink-0" /><span>3. 48小时内向合规委员会提交书面报备</span></div>
                                        <div className="flex items-center space-x-2"><Shield size={11} className="text-amber-500 shrink-0" /><span>4. 如仍需承接，须获得双方客户书面知情同意</span></div>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
