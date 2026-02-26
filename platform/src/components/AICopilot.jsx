import { useState, useEffect, useRef } from 'react';
import { Send, X, MessageSquare, Sparkles, Command, Loader2 } from 'lucide-react';

// 模拟 AI 回复 — 根据关键词匹配不同法律场景回复
const aiResponses = {
    '投标': '根据本所《投标管理系统》检索，您上周提交的"某市政府法律顾问采购项目"投标文件已通过内部合规审核。\n\n📋 标书评分预估：86/100\n✅ 资质匹配：5/6 项达标\n⚠️ 建议：补充信息安全管理措施说明（ISO27001 要求）\n\n需要我打开投标中心为您查看详情吗？',
    '利冲': '正在检索本所私有知识图谱...\n\n🔍 利冲快速检索结果：\n输入实体「腾讯」→ 穿透识别到 2 条关联记录\n• 腾讯控股 — 历史在办（2023年并购项目）\n• 腾讯科技 — 当前顾问（常年法律顾问）\n\n⚠️ 风险等级：HIGH\n建议立即启动信息隔离墙（Chinese Wall）程序。',
    '合同': '已连接合同模板库，为您检索到以下匹配模板：\n\n1. 📄 《政府采购合同（服务类）》v3.2\n2. 📄 《常年法律顾问聘用合同》v2.1\n3. 📄 《保密协议（政府项目专用）》v4.0\n\n所有模板均已通过 2026 年最新法规合规审查。需要我为您预填充项目信息吗？',
    '脱敏': '本所 NER 脱敏引擎当前状态：\n\n🟢 运行正常 | 今日调用 12,842 次\n• 人名识别准确率：98.7%\n• 身份证/银行卡：99.2%\n• 法律案号：97.5%\n\n所有外发至 LLM 的文本均经过脱敏网关处理，确保客户隐私数据不出本所网络。',
    'default': '已收到您的问题。我正在为您检索本所私有知识库...\n\n根据《民事诉讼业务内控准则》第 12 条及《合规管理办法》相关规定，您的查询涉及以下要点：\n\n1. 利益冲突审查应在承接业务前 48 小时内完成\n2. 涉敏文件须通过 NER 脱敏网关处理后方可外发\n3. 重大项目需经合伙人会议审批\n\n如需进一步了解，请指定具体条款编号。'
};

function getAIResponse(input) {
    const lower = input.toLowerCase();
    for (const [key, response] of Object.entries(aiResponses)) {
        if (key !== 'default' && lower.includes(key)) return response;
    }
    return aiResponses['default'];
}

export default function AICopilot() {
    const [isOpen, setIsOpen] = useState(false);
    const [input, setInput] = useState('');
    const [msgs, setMsgs] = useState([
        { r: 'ai', t: '你好，我是 Legal-AI 算力助手。我可以为您检索律所私有知识库，或者执行业务 Agent 调用指令。\n\n💡 试试问我：投标进度、利冲检索、合同模板、脱敏状态', done: true }
    ]);
    const [isTyping, setIsTyping] = useState(false);
    const scrollRef = useRef(null);
    const typingRef = useRef(null);

    const send = (e) => {
        e.preventDefault();
        if (!input.trim() || isTyping) return;

        const userMsg = input;
        const newMsgs = [...msgs, { r: 'u', t: userMsg, done: true }];
        setMsgs(newMsgs);
        setInput('');
        setIsTyping(true);

        // 加载态
        const withLoading = [...newMsgs, { r: 'ai', t: '', loading: true, done: false }];
        setMsgs(withLoading);

        // 800ms 后开始打字
        setTimeout(() => {
            const fullResponse = getAIResponse(userMsg);
            const baseMessages = [...newMsgs];
            let charIndex = 0;

            typingRef.current = setInterval(() => {
                charIndex += 2;
                if (charIndex >= fullResponse.length) {
                    charIndex = fullResponse.length;
                    clearInterval(typingRef.current);
                    setIsTyping(false);
                }
                setMsgs([...baseMessages, { r: 'ai', t: fullResponse.slice(0, charIndex), done: charIndex >= fullResponse.length }]);
            }, 20);
        }, 800);
    };

    useEffect(() => {
        if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }, [msgs, isOpen]);

    useEffect(() => {
        return () => { if (typingRef.current) clearInterval(typingRef.current); };
    }, []);

    return (
        <div className="fixed bottom-6 right-6 z-[60] flex flex-col items-end">
            {isOpen && (
                <div className="w-[400px] h-[560px] bg-[#1a1c23] border border-zinc-700 rounded-lg shadow-2xl flex flex-col overflow-hidden zoom-in">
                    <div className="h-12 bg-[#232f3e] px-4 flex items-center justify-between border-b border-zinc-800 shrink-0">
                        <div className="flex items-center space-x-2 text-white font-bold text-xs uppercase tracking-widest">
                            <Sparkles size={14} className="text-orange-400" /><span>Legal-AI Copilot</span>
                        </div>
                        <div className="flex items-center space-x-3">
                            <span className="text-[9px] text-emerald-500 font-bold flex items-center"><span className="w-1.5 h-1.5 bg-emerald-500 rounded-full mr-1 animate-pulse"></span>VPC Connected</span>
                            <button onClick={() => setIsOpen(false)} className="text-zinc-400 hover:text-white"><X size={16} /></button>
                        </div>
                    </div>
                    <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4 font-mono text-[11px] bg-black/20">
                        {msgs.map((m, i) => (
                            <div key={i} className={`flex ${m.r === 'ai' ? 'justify-start' : 'justify-end'}`}>
                                <div className={`max-w-[85%] p-3 rounded-sm leading-relaxed shadow-lg ${m.r === 'ai' ? 'bg-zinc-800/90 text-zinc-300 border-l-2 border-orange-500' : 'bg-blue-900/40 text-blue-100 border border-blue-800'
                                    }`}>
                                    {m.r === 'ai' && <div className="text-[9px] text-zinc-500 mb-1 font-bold uppercase tracking-tighter">Instance Output</div>}
                                    {m.loading ? (
                                        <div className="flex items-center space-x-2">
                                            <Loader2 size={12} className="animate-spin text-orange-400" />
                                            <span className="text-[10px] text-zinc-500 animate-pulse">Processing via VPC Internal...</span>
                                        </div>
                                    ) : (
                                        <span className="whitespace-pre-wrap">{m.t}{!m.done && <span className="inline-block w-1.5 h-3.5 bg-orange-500 ml-0.5 animate-pulse"></span>}</span>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                    <div className="p-4 border-t border-zinc-800 bg-[#1c222d] shrink-0">
                        <form onSubmit={send} className="relative">
                            <input value={input} onChange={(e) => setInput(e.target.value)} type="text"
                                placeholder={isTyping ? "AI 正在回复..." : "键入法律问题或控制指令..."}
                                disabled={isTyping}
                                className="w-full bg-zinc-900 border border-zinc-700 rounded-sm py-2.5 pl-4 pr-10 text-[11px] text-zinc-300 focus:outline-none focus:border-orange-500 font-mono shadow-inner disabled:opacity-50" />
                            <button type="submit" disabled={isTyping} className="absolute right-2 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-orange-500 transition-colors disabled:opacity-30"><Send size={16} /></button>
                        </form>
                        <div className="mt-3 flex justify-between text-[9px] font-bold text-zinc-600 uppercase tracking-tighter">
                            <span>Private Inference Mode · AES-256 Encrypted</span>
                            <div className="flex items-center space-x-1"><Command size={10} /><span>K</span></div>
                        </div>
                    </div>
                </div>
            )}
            {!isOpen && (
                <button onClick={() => setIsOpen(true)} className="bg-orange-500 text-white p-4 rounded-full shadow-2xl hover:bg-orange-600 transition-all hover:scale-110 active:scale-95 group relative ring-4 ring-orange-500/20">
                    <MessageSquare size={24} />
                    <span className="absolute -top-1 -right-1 w-3.5 h-3.5 bg-red-600 rounded-full border-2 border-white animate-pulse"></span>
                </button>
            )}
        </div>
    );
}
