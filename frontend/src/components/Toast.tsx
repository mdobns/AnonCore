import { AnimatePresence, motion } from 'framer-motion';
import { useUIStore } from '../store/uiStore';

const ICONS: Record<string, string> = {
  info: 'ℹ',
  success: '✓',
  warning: '⚠',
  error: '✕',
};

export function ToastContainer() {
  const { toasts, removeToast } = useUIStore();

  return (
    <div className="toast-container" aria-live="polite">
      <AnimatePresence initial={false}>
        {toasts.map((t) => (
          <motion.div
            key={t.id}
            className={`toast ${t.kind}`}
            initial={{ x: 40, opacity: 0, scale: 0.92 }}
            animate={{ x: 0, opacity: 1, scale: 1 }}
            exit={{ x: 40, opacity: 0, scale: 0.9 }}
            transition={{ duration: 0.22, ease: [0.34, 1.56, 0.64, 1] }}
            layout
          >
            <span style={{ fontSize: 14, lineHeight: 1, flexShrink: 0 }}>{ICONS[t.kind]}</span>
            <span style={{ flex: 1 }}>{t.message}</span>
            <button className="toast-close" onClick={() => removeToast(t.id)} aria-label="Dismiss">
              ✕
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
