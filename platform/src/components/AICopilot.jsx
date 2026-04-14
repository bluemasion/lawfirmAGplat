import { useState, useEffect, useRef } from 'react';
import { Send, X, MessageSquare, Sparkles, Command, Loader2 } from 'lucide-react';

// 后端 API 地址
const API_BASE = 'http://localhost:8001';

export default function AICopilot() {
    const [isOpen, setIsOpen] = useState(false);
    const [input, setInput] = useState('');
    const [msgs, setMsgs] = useState([
        { r: 'ai', t: '你好，我是 Legal-AI 算力助手。我已连接通义千问大模型，可以为您提供实时法律咨询。\n\n💡 试试问我：\n• 什么是利益冲突？律所如何管理？\n• 政府采购法律顾问招标要注意什么？\n• 帮我分析一段合同条款的风险\n• NER 脱敏的技术原理是什么？', done: true }
    ]);
    const [isTyping, setIsTyping] = useState(false);
    const scrollRef = useRef(null);
    const abortRef = useRef(null);

    const send = async (e) => {
        e.preventDefault();
        if (!input.trim() || isTyping) return;

        const userMsg = input.trim();
        const newMsgs = [...msgs, { r: 'u', t: userMsg, done: true }];
        setMsgs(newMsgs);
        setInput('');
        setIsTyping(true);

        // 显示加载态
        const loadingMsgs = [...newMsgs, { r: 'ai', t: '', loading: true, done: false }];
        setMsgs(loadingMsgs);

        try {
            const controller = new AbortController();
            abortRef.current = controller;

            const response = await fetch(`${API_BASE}/api/chat/completions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: userMsg, stream: true }),
                signal: controller.signal,
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let fullContent = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const text = decoder.decode(value, { stream: true });
                const lines = text.split('\n');

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    try {
                        const data = JSON.parse(line.slice(6));
                        if (data.done) break;
                        fullContent += data.content;
                        setMsgs([...newMsgs, { r: 'ai', t: fullContent, done: false }]);
                    } catch (e) {
                        // ignore parse errors on partial chunks
                    }
                }
            }

            setMsgs([...newMsgs, { r: 'ai', t: fullContent || '[无响应]', done: true }]);
        } catch (err) {
            if (err.name === 'AbortError') return;
            console.error('Chat error:', err);
            // 降级到 mock 响应
            const fallbackMsg = `[连接后端失败: ${err.message}]\n\n系统已切换为离线模式。请确认后端服务运行在 localhost:8000。`;
            setMsgs([...newMsgs, { r: 'ai', t: fallbackMsg, done: true }]);
        } finally {
            setIsTyping(false);
            abortRef.current = null;
        }
    };

    useEffect(() => {
        if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }, [msgs, isOpen]);

    useEffect(() => {
        return () => { if (abortRef.current) abortRef.current.abort(); };
    }, []);

    return (
        <div className="fixed bottom-6 right-6 z-[60] flex flex-col items-end">
            {isOpen && (
                <div className="w-[420px] h-[580px] bg-[#1a1c23] border border-zinc-700 rounded-lg shadow-2xl flex flex-col overflow-hidden zoom-in">
                    <div className="h-12 bg-[#232f3e] px-4 flex items-center justify-between border-b border-zinc-800 shrink-0">
                        <div className="flex items-center space-x-2 text-white font-bold text-xs uppercase tracking-widest">
                            <Sparkles size={14} className="text-orange-400" /><span>Legal-AI Copilot</span>
                        </div>
                        <div className="flex items-center space-x-3">
                            <span className="text-[9px] text-emerald-500 font-bold flex items-center"><span className="w-1.5 h-1.5 bg-emerald-500 rounded-full mr-1 animate-pulse"></span>Qwen-Max · VPC</span>
                            <button onClick={() => setIsOpen(false)} className="text-zinc-400 hover:text-white"><X size={16} /></button>
                        </div>
                    </div>
                    <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4 font-mono text-[11px] bg-black/20">
                        {msgs.map((m, i) => (
                            <div key={i} className={`flex ${m.r === 'ai' ? 'justify-start' : 'justify-end'}`}>
                                <div className={`max-w-[88%] p-3 rounded-sm leading-relaxed shadow-lg ${m.r === 'ai' ? 'bg-zinc-800/90 text-zinc-300 border-l-2 border-orange-500' : 'bg-blue-900/40 text-blue-100 border border-blue-800'
                                    }`}>
                                    {m.r === 'ai' && <div className="text-[9px] text-zinc-500 mb-1 font-bold uppercase tracking-tighter">Qwen-Max Output</div>}
                                    {m.loading ? (
                                        <div className="flex items-center space-x-2">
                                            <Loader2 size={12} className="animate-spin text-orange-400" />
                                            <span className="text-[10px] text-zinc-500 animate-pulse">Connecting to Qwen-Max via VPC...</span>
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
                            <span>🔒 NER Gateway · AES-256 Encrypted</span>
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
