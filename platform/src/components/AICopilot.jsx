import { useState, useEffect, useRef } from 'react';
import { Send, X, MessageSquare, Sparkles, Command } from 'lucide-react';

export default function AICopilot() {
    const [isOpen, setIsOpen] = useState(false);
    const [input, setInput] = useState('');
    const [msgs, setMsgs] = useState([
        { r: 'ai', t: '你好，我是 Legal-AI 算力助手。我可以为您检索律所私有知识库，或者执行业务 Agent 调用指令。' }
    ]);
    const scrollRef = useRef(null);

    const send = (e) => {
        e.preventDefault();
        if (!input.trim()) return;
        const n = [...msgs, { r: 'u', t: input }];
        setMsgs(n);
        setInput('');
        setTimeout(() => setMsgs([...n, { r: 'ai', t: '[VPC_INTERNAL] 正在为您检索本所《民事诉讼业务内控准则》... 发现 2 条匹配条款。' }]), 800);
    };

    useEffect(() => {
        if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }, [msgs, isOpen]);

    return (
        <div className="fixed bottom-6 right-6 z-[60] flex flex-col items-end">
            {isOpen && (
                <div className="w-[380px] h-[520px] bg-[#1a1c23] border border-zinc-700 rounded-lg shadow-2xl flex flex-col overflow-hidden zoom-in">
                    <div className="h-12 bg-[#232f3e] px-4 flex items-center justify-between border-b border-zinc-800 shrink-0">
                        <div className="flex items-center space-x-2 text-white font-bold text-xs uppercase tracking-widest">
                            <Sparkles size={14} className="text-orange-400" /><span>Legal-AI Copilot</span>
                        </div>
                        <button onClick={() => setIsOpen(false)} className="text-zinc-400 hover:text-white"><X size={16} /></button>
                    </div>
                    <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4 font-mono text-[11px] bg-black/20">
                        {msgs.map((m, i) => (
                            <div key={i} className={`flex ${m.r === 'ai' ? 'justify-start' : 'justify-end'}`}>
                                <div className={`max-w-[85%] p-3 rounded-sm leading-relaxed shadow-lg ${m.r === 'ai' ? 'bg-zinc-800/90 text-zinc-300 border-l-2 border-orange-500' : 'bg-blue-900/40 text-blue-100 border border-blue-800'}`}>
                                    {m.r === 'ai' && <div className="text-[9px] text-zinc-500 mb-1 font-bold uppercase tracking-tighter">Instance Output</div>}
                                    {m.t}
                                </div>
                            </div>
                        ))}
                    </div>
                    <div className="p-4 border-t border-zinc-800 bg-[#1c222d] shrink-0">
                        <form onSubmit={send} className="relative">
                            <input value={input} onChange={(e) => setInput(e.target.value)} type="text" placeholder="键入法律问题或控制指令..."
                                className="w-full bg-zinc-900 border border-zinc-700 rounded-sm py-2.5 pl-4 pr-10 text-[11px] text-zinc-300 focus:outline-none focus:border-orange-500 font-mono shadow-inner" />
                            <button type="submit" className="absolute right-2 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-orange-500 transition-colors"><Send size={16} /></button>
                        </form>
                        <div className="mt-3 flex justify-between text-[9px] font-bold text-zinc-600 uppercase tracking-tighter">
                            <span>Private Inference Mode Active</span>
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
