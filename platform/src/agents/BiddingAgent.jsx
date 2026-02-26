import { useState, useEffect, useRef } from 'react';
import { ArrowLeft, Upload, FileText, CheckCircle, AlertTriangle, Loader2, ChevronRight, Download, Search, Shield } from 'lucide-react';

// 政府法律顾问采购 — mock 数据
const tenderInfo = {
    projectName: '某市人民政府2026年度常年法律顾问服务采购项目',
    tenderNo: 'GKCG-2026-0318',
    budget: '¥120万元/年',
    deadline: '2026-03-18 17:00',
    serviceScope: '政府决策合法性审查、规范性文件审核、行政复议/诉讼代理、重大项目法律论证',
    requirements: [
        { item: '律所执业年限≥10年', match: true },
        { item: '具有政府法律顾问服务经验≥3年', match: true },
        { item: '拟派团队≥3名执业律师', match: true },
        { item: '近3年无行业处罚记录', match: true },
        { item: '具备ISO27001信息安全认证', match: false },
    ],
    scoring: [
        { category: '技术方案', weight: 55, details: '服务方案30分 + 团队配置15分 + 创新方案10分' },
        { category: '商务报价', weight: 30, details: '价格分=最低报价/投标报价×30' },
        { category: '业绩与资质', weight: 15, details: '同类业绩10分 + 律所荣誉5分' },
    ],
};

const draftChapters = [
    { title: '第一章 律所概况及资质', icon: '🏛️', active: false },
    { title: '第二章 项目理解与分析', icon: '📋', active: false },
    { title: '第三章 服务方案', icon: '⚖️', active: true },
    { title: '第四章 项目团队配置', icon: '👥', active: false },
    { title: '第五章 报价方案', icon: '💰', active: false },
    { title: '第六章 增值服务', icon: '🌟', active: false },
];

const draftContent = `## 三、服务方案

### 3.1 常年法律顾问服务框架

根据贵市政府的实际需求及本次招标文件要求，我所将提供以下六大模块的法律顾问服务：

**模块一：政府决策合法性审查**
- 对政府重大行政决策进行合法性审查，出具书面法律意见
- 对规范性文件进行合法性审核，确保与上位法一致
- 建立"事前审查 + 事中监控 + 事后评估"三阶段工作机制

**模块二：合同与协议管理**
- 审查、修订各类政府采购合同、投资协议、合作框架协议
- 建立合同模板库（覆盖工程建设、货物采购、服务外包等12个领域）
- 重大合同实行"双律师会签"制度，确保审核质量

**模块三：行政争议处理**
- 代理行政复议案件，参与行政诉讼应诉
- 处理信息公开申请的法律审核
- 处理重大信访事项的法律意见出具

**模块四：专项法律服务**
- 城市更新、征地拆迁项目法律论证
- PPP/EOD项目合规审查
- 政府债务风险防控法律建议`;

const complianceChecks = [
    { label: '文件格式合规 (GB/T 9704-2012)', pass: true, detail: '页面设置、字体字号、行间距均符合规范' },
    { label: '必选项完整性', pass: true, detail: '6/6 章节均已覆盖招标文件强制响应项' },
    { label: '资质匹配度', pass: false, detail: '缺少 ISO27001 信息安全认证 → 建议补充信息安全管理措施说明' },
    { label: '报价合理性', pass: true, detail: '报价 ¥98万/年，低于预算上限 ¥120万，竞争力系数 0.82' },
    { label: '禁用表述检查', pass: true, detail: '未发现《律师法》禁止用语及虚假承诺表述' },
    { label: '团队合规', pass: true, detail: '3名拟派律师均执业证有效，无不良记录' },
];

export default function BiddingAgent({ onBack }) {
    const [step, setStep] = useState(0); // 0=上传, 1=分析, 2=生成
    const [fileName, setFileName] = useState('');
    const [analysisItems, setAnalysisItems] = useState([]);
    const [typedContent, setTypedContent] = useState('');
    const [activeChapter, setActiveChapter] = useState(2);
    const contentRef = useRef(null);

    // 模拟文件上传
    const handleUpload = () => {
        setFileName('某市政府法律顾问招标文件-GKCG-2026-0318.pdf');
        setTimeout(() => setStep(1), 600);
    };

    // 步骤2: 逐项分析动画
    useEffect(() => {
        if (step !== 1) return;
        const items = [
            { label: '项目名称', value: tenderInfo.projectName, delay: 400 },
            { label: '招标编号', value: tenderInfo.tenderNo, delay: 700 },
            { label: '预算金额', value: tenderInfo.budget, delay: 1000 },
            { label: '投标截止', value: tenderInfo.deadline, delay: 1300 },
            { label: '服务范围', value: tenderInfo.serviceScope, delay: 1600 },
        ];
        items.forEach(({ label, value, delay }) => {
            setTimeout(() => setAnalysisItems(prev => [...prev, { label, value }]), delay);
        });
        setTimeout(() => setStep(2), 3200);
    }, [step]);

    // 步骤3: 打字机效果输出草案
    useEffect(() => {
        if (step !== 2) return;
        let i = 0;
        const timer = setInterval(() => {
            setTypedContent(draftContent.slice(0, i));
            i += 3;
            if (i > draftContent.length) {
                setTypedContent(draftContent);
                clearInterval(timer);
            }
        }, 10);
        return () => clearInterval(timer);
    }, [step]);

    useEffect(() => {
        if (contentRef.current) contentRef.current.scrollTop = contentRef.current.scrollHeight;
    }, [typedContent]);

    const stepLabels = [
        { label: '上传招标文件', desc: '导入招标公告及技术要求' },
        { label: 'AI 智能解析', desc: '提取关键信息与资质要求' },
        { label: '生成投标文件', desc: '智能编排标书草案 + 合规审核' },
    ];

    return (
        <div className="p-6 space-y-5 animate-in">
            {/* 标题 */}
            <div className="flex items-center space-x-3 border-b border-zinc-200 pb-4">
                <button onClick={onBack} className="text-zinc-400 hover:text-zinc-700"><ArrowLeft size={16} /></button>
                <div>
                    <h2 className="text-lg font-bold text-zinc-800 uppercase tracking-tight">智能投标中心 (Bidding Studio)</h2>
                    <p className="text-[10px] text-zinc-400 font-bold uppercase tracking-widest">AI-Powered Bid Document Generation with Compliance Guardrails</p>
                </div>
            </div>

            {/* 步骤条 */}
            <div className="flex items-center space-x-2">
                {stepLabels.map((s, i) => (
                    <div key={i} className="flex items-center">
                        <div className={`flex items-center space-x-2 px-4 py-2.5 rounded-sm border transition-all ${i < step ? 'bg-emerald-50 border-emerald-200' :
                                i === step ? 'bg-blue-50 border-blue-300 ring-1 ring-blue-200' :
                                    'bg-zinc-50 border-zinc-200'
                            }`}>
                            {i < step ? <CheckCircle size={14} className="text-emerald-600 shrink-0" /> :
                                i === step ? <div className="w-3.5 h-3.5 border-2 border-blue-500 rounded-full border-t-transparent animate-spin shrink-0"></div> :
                                    <div className="w-3.5 h-3.5 border-2 border-zinc-300 rounded-full shrink-0"></div>}
                            <div>
                                <p className={`text-[11px] font-bold ${i < step ? 'text-emerald-700' : i === step ? 'text-blue-700' : 'text-zinc-400'}`}>{s.label}</p>
                                <p className="text-[9px] text-zinc-400">{s.desc}</p>
                            </div>
                        </div>
                        {i < stepLabels.length - 1 && <ChevronRight size={14} className="text-zinc-300 mx-1" />}
                    </div>
                ))}
            </div>

            {/* 步骤 0: 上传 */}
            {step === 0 && (
                <div className="slide-up max-w-2xl mx-auto">
                    <div onClick={handleUpload}
                        className="border-2 border-dashed border-zinc-300 rounded-sm p-12 text-center cursor-pointer hover:border-blue-400 hover:bg-blue-50/30 transition-all group">
                        <Upload size={40} className="mx-auto text-zinc-300 group-hover:text-blue-500 transition mb-4" />
                        <p className="text-sm font-bold text-zinc-600 mb-1">点击此处上传招标文件</p>
                        <p className="text-[10px] text-zinc-400">支持 PDF / DOCX / ZIP，最大 50MB</p>
                    </div>
                    <div className="mt-4 bg-zinc-50 border border-zinc-200 rounded-sm p-4">
                        <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-2">💡 演示说明</p>
                        <p className="text-[11px] text-zinc-500">点击上传区域将使用内置的「某市人民政府2026年度常年法律顾问服务采购项目」招标文件进行演示。系统将自动解析文件内容并提取关键信息。</p>
                    </div>
                </div>
            )}

            {/* 步骤 1: AI 分析 */}
            {step === 1 && (
                <div className="slide-up max-w-3xl mx-auto space-y-4">
                    <div className="bg-white border border-zinc-200 rounded-sm p-5 shadow-sm">
                        <div className="flex items-center space-x-2 mb-4">
                            <FileText size={14} className="text-blue-600" />
                            <span className="text-xs font-bold text-zinc-700">{fileName}</span>
                            <span className="text-[10px] text-zinc-400 italic">( 36 页 · 2.4 MB )</span>
                        </div>
                        <div className="space-y-2">
                            {analysisItems.map((item, i) => (
                                <div key={i} className="flex items-center space-x-3 py-2 px-3 bg-zinc-50 rounded-sm border border-zinc-100 slide-up">
                                    <Search size={12} className="text-blue-500 shrink-0" />
                                    <span className="text-[10px] font-bold text-zinc-500 uppercase w-20 shrink-0">{item.label}</span>
                                    <span className="text-xs text-zinc-800 font-medium">{item.value}</span>
                                </div>
                            ))}
                            {analysisItems.length < 5 && (
                                <div className="flex items-center space-x-2 py-3 text-center justify-center">
                                    <Loader2 size={14} className="animate-spin text-blue-500" />
                                    <span className="text-[10px] text-blue-600 font-bold animate-pulse uppercase">AI Parsing Document...</span>
                                </div>
                            )}
                        </div>
                    </div>

                    {analysisItems.length >= 4 && (
                        <div className="slide-up">
                            <h4 className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-2">📊 资质匹配分析</h4>
                            <div className="grid grid-cols-1 gap-1.5">
                                {tenderInfo.requirements.map((r, i) => (
                                    <div key={i} className="flex items-center space-x-2 py-2 px-3 bg-white border border-zinc-100 rounded-sm slide-up">
                                        {r.match ? <CheckCircle size={13} className="text-emerald-500 shrink-0" /> : <AlertTriangle size={13} className="text-amber-500 shrink-0" />}
                                        <span className={`text-[11px] ${r.match ? 'text-zinc-700' : 'text-amber-700 font-bold'}`}>{r.item}</span>
                                        {!r.match && <span className="text-[9px] text-amber-500 italic ml-auto">需补充说明</span>}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {analysisItems.length >= 4 && (
                        <div className="slide-up">
                            <h4 className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-2">📐 评分标准</h4>
                            <div className="grid grid-cols-3 gap-2">
                                {tenderInfo.scoring.map((s, i) => (
                                    <div key={i} className="bg-white border border-zinc-200 rounded-sm p-3">
                                        <div className="flex justify-between items-center mb-1.5">
                                            <span className="text-[11px] font-bold text-zinc-700">{s.category}</span>
                                            <span className="text-sm font-bold text-blue-600">{s.weight}分</span>
                                        </div>
                                        <div className="w-full bg-zinc-100 h-1.5 rounded-full mb-1.5"><div className="h-full bg-blue-500 rounded-full" style={{ width: `${s.weight}%` }}></div></div>
                                        <p className="text-[9px] text-zinc-400">{s.details}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* 步骤 2: 生成标书 */}
            {step === 2 && (
                <div className="grid grid-cols-12 gap-4 slide-up" style={{ height: 'calc(100vh - 240px)' }}>
                    {/* 左侧目录 */}
                    <div className="col-span-2 bg-white border border-zinc-200 rounded-sm overflow-hidden">
                        <div className="px-3 py-2.5 bg-zinc-50 border-b border-zinc-200 text-[9px] font-bold text-zinc-500 uppercase tracking-widest">标书目录</div>
                        <div className="p-1">
                            {draftChapters.map((c, i) => (
                                <button key={i} onClick={() => setActiveChapter(i)}
                                    className={`w-full text-left px-2.5 py-2 rounded-sm text-[10px] transition-all mb-0.5 ${i === activeChapter ? 'bg-blue-50 text-blue-700 font-bold border border-blue-200' : 'text-zinc-600 hover:bg-zinc-50'
                                        }`}>
                                    <span className="mr-1">{c.icon}</span>{c.title}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* 中间内容 */}
                    <div className="col-span-6 bg-white border border-zinc-200 rounded-sm overflow-hidden flex flex-col shadow-sm">
                        <div className="px-4 py-2.5 bg-zinc-50 border-b border-zinc-200 flex items-center justify-between">
                            <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-widest">标书草案预览 (AI Draft)</span>
                            <div className="flex items-center space-x-1 text-[9px] text-blue-500 font-bold">
                                <Loader2 size={10} className={typedContent.length < draftContent.length ? 'animate-spin' : 'hidden'} />
                                <span>{typedContent.length < draftContent.length ? 'Generating...' : 'Complete'}</span>
                            </div>
                        </div>
                        <div ref={contentRef} className="flex-1 overflow-y-auto p-6 text-[12px] text-zinc-700 leading-relaxed font-serif whitespace-pre-wrap">
                            {typedContent || <div className="flex items-center justify-center h-full"><Loader2 size={20} className="animate-spin text-blue-500" /></div>}
                        </div>
                    </div>

                    {/* 右侧面板 */}
                    <div className="col-span-4 space-y-3 overflow-y-auto">
                        {/* 合规审核 */}
                        <div className="bg-[#151921] border border-zinc-700 rounded-sm p-4 text-white shadow-inner">
                            <div className="flex items-center space-x-2 mb-3">
                                <Shield size={13} className="text-emerald-400" />
                                <span className="text-[9px] font-bold text-zinc-400 uppercase tracking-widest">合规审核面板 (Compliance)</span>
                            </div>
                            <div className="space-y-2">
                                {complianceChecks.map((c, i) => (
                                    <div key={i} className="flex items-start space-x-2 py-1.5">
                                        {c.pass ? <CheckCircle size={12} className="text-emerald-500 mt-0.5 shrink-0" /> : <AlertTriangle size={12} className="text-amber-500 mt-0.5 shrink-0" />}
                                        <div>
                                            <p className={`text-[10px] font-bold ${c.pass ? 'text-emerald-400' : 'text-amber-400'}`}>{c.label}</p>
                                            <p className="text-[9px] text-zinc-500 mt-0.5">{c.detail}</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* 评分预估 */}
                        <div className="bg-white border border-zinc-200 rounded-sm p-4">
                            <p className="text-[9px] font-bold text-zinc-500 uppercase tracking-widest mb-2">预估评分</p>
                            <div className="space-y-2">
                                {[{ cat: '技术方案', score: 48, max: 55 }, { cat: '商务报价', score: 25, max: 30 }, { cat: '业绩资质', score: 13, max: 15 }].map((s, i) => (
                                    <div key={i}>
                                        <div className="flex justify-between text-[10px] mb-1"><span className="text-zinc-600 font-bold">{s.cat}</span><span className="text-blue-600 font-bold">{s.score}/{s.max}</span></div>
                                        <div className="w-full bg-zinc-100 h-1.5 rounded-full overflow-hidden"><div className="h-full bg-blue-500 rounded-full transition-all" style={{ width: `${(s.score / s.max) * 100}%` }}></div></div>
                                    </div>
                                ))}
                                <div className="mt-2 pt-2 border-t border-zinc-200 flex justify-between">
                                    <span className="text-xs font-bold text-zinc-800">总分预估</span>
                                    <span className="text-lg font-bold text-blue-600">86<span className="text-xs text-zinc-400">/100</span></span>
                                </div>
                            </div>
                        </div>

                        {/* 操作按钮 */}
                        <button className="w-full py-3 bg-blue-600 text-white text-xs font-bold rounded-sm uppercase tracking-tight hover:bg-blue-700 transition shadow-lg flex items-center justify-center space-x-2">
                            <Download size={14} /><span>导出投标文件 (.docx)</span>
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
