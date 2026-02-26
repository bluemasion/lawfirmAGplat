import { useState, useEffect } from 'react';
import { FileCheck, Languages, Search, FileSignature, ChevronRight } from 'lucide-react';
import { getAgentApps } from '../api/services';

const iconMap = { securities: FileCheck, translation: Languages, conflict: Search, bidding: FileSignature };

export default function AppCenter({ onSelectAgent }) {
    const [apps, setApps] = useState([]);
    useEffect(() => { getAgentApps().then(setApps); }, []);

    return (
        <div className="p-8 space-y-8 animate-in">
            <div className="border-b border-zinc-200 pb-4 flex justify-between items-end">
                <div>
                    <h2 className="text-xl font-bold text-zinc-800 uppercase tracking-tighter italic">应用中心 / APP DIRECTORY</h2>
                    <p className="text-[10px] text-zinc-400 font-bold uppercase tracking-widest mt-1">Select Service to Launch Dedicated Console</p>
                </div>
                <button className="px-4 py-1.5 border border-zinc-300 rounded-sm text-[10px] font-bold text-zinc-600 hover:bg-zinc-50 uppercase tracking-widest">Update Catalog</button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pb-20">
                {apps.map((app) => {
                    const Icon = iconMap[app.id] || FileCheck;
                    return (
                        <div key={app.id} onClick={() => onSelectAgent(app.id)}
                            className="bg-white border border-zinc-200 flex items-stretch hover:border-blue-600 hover:shadow-2xl transition-all cursor-pointer group rounded-sm shadow-sm overflow-hidden">
                            <div className="w-20 bg-zinc-50 flex items-center justify-center text-zinc-400 group-hover:text-blue-600 transition-colors border-r border-zinc-100">
                                <Icon size={32} />
                            </div>
                            <div className="p-6 flex-1 space-y-2">
                                <div className="flex justify-between items-start">
                                    <h3 className="font-bold text-zinc-800 text-sm group-hover:text-blue-600 uppercase tracking-tight">{app.title}</h3>
                                    <span className="text-[9px] font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-sm border border-emerald-100 italic uppercase">{app.status}</span>
                                </div>
                                <p className="text-[11px] text-zinc-500 font-bold italic line-clamp-2 leading-relaxed opacity-80">{app.desc}</p>
                                <div className="pt-4 flex items-center text-[10px] font-bold text-blue-600 opacity-0 group-hover:opacity-100 transition-all transform translate-y-1 group-hover:translate-y-0">
                                    <span>启动业务控制台</span><ChevronRight size={12} className="ml-1" />
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
