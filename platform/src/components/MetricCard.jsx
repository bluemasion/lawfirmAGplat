import { useState, useEffect } from 'react';
import { MoreHorizontal } from 'lucide-react';

export default function MetricCard({ label, value, trend, unit }) {
    const [displayValue, setDisplayValue] = useState('');
    const [animated, setAnimated] = useState(false);

    useEffect(() => {
        if (animated || !value) return;

        // 提取数字部分
        const cleanValue = String(value).replace(/,/g, '');
        const numMatch = cleanValue.match(/([\d.]+)/);
        if (!numMatch) { setDisplayValue(value); setAnimated(true); return; }

        const target = parseFloat(numMatch[0]);
        const isFloat = numMatch[0].includes('.');
        const idx = cleanValue.indexOf(numMatch[0]);
        const prefix = cleanValue.slice(0, idx);
        const suffix = cleanValue.slice(idx + numMatch[0].length);
        const originalHasComma = String(value).includes(',');

        const duration = 1000;
        const startTime = performance.now();

        const animate = (now) => {
            const elapsed = now - startTime;
            const progress = Math.min(elapsed / duration, 1);
            // easeOutExpo
            const eased = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
            const current = target * eased;

            let formatted;
            if (isFloat) {
                formatted = current.toFixed(2);
            } else {
                const intVal = Math.round(current);
                formatted = originalHasComma ? intVal.toLocaleString() : String(intVal);
            }

            setDisplayValue(prefix + formatted + suffix);

            if (progress < 1) {
                requestAnimationFrame(animate);
            } else {
                setDisplayValue(value);
                setAnimated(true);
            }
        };

        requestAnimationFrame(animate);
    }, [value, animated]);

    return (
        <div className="bg-white border border-zinc-200 p-4 rounded-sm shadow-sm hover:shadow-md transition-all group">
            <div className="flex justify-between items-start mb-2">
                <span className="text-zinc-500 text-[10px] font-bold uppercase tracking-widest">{label}</span>
                <MoreHorizontal size={14} className="text-zinc-400 opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer" />
            </div>
            <div className="flex items-baseline space-x-1">
                <span className="text-2xl font-bold text-zinc-900 tracking-tight">{displayValue || '0'}</span>
                {unit && <span className="text-xs text-zinc-400 font-bold">{unit}</span>}
            </div>
            {trend && (
                <div className="mt-2 flex items-center text-[10px] font-bold">
                    <span className={trend.startsWith('+') ? 'text-emerald-600' : 'text-rose-600'}>{trend}</span>
                    <span className="text-zinc-400 ml-1 font-medium text-[9px]">较昨日</span>
                </div>
            )}
        </div>
    );
}
