import { clamp, escapeHtml } from './core.mjs';

const scrollInset = 24;

export class Reader {
  constructor(view, flow, onChange) {
    this.view = view;
    this.flow = flow;
    this.onChange = onChange;
    this.page = 0;
    this.total = 1;
    this.mode = 'scroll';
    this.sections = [];
    this.anchor = null;
    this.resizeObserver = new ResizeObserver(() => this.scheduleLayout());
    this.resizeObserver.observe(view);
    window.addEventListener('scroll', () => {
      if (this.mode !== 'scroll') return;
      cancelAnimationFrame(this.pendingReport);
      this.pendingReport = requestAnimationFrame(() => this.report());
    }, { passive: true });
    view.addEventListener('pointerdown', event => {
      if (event.pointerType === 'touch' && event.isPrimary) this.touch = { x: event.clientX, y: event.clientY };
    }, { passive: true });
    view.addEventListener('pointerup', event => {
      const touch = this.touch;
      this.touch = null;
      if (!touch || this.mode !== 'pages') return;
      const dx = event.clientX - touch.x;
      const dy = event.clientY - touch.y;
      if (Math.abs(dx) > 45 && Math.abs(dx) > Math.abs(dy) * 1.4 && !getSelection()?.toString()) this.turn(dx < 0 ? 1 : -1);
    }, { passive: true });
    view.addEventListener('pointercancel', () => { this.touch = null; }, { passive: true });
  }

  render(rite, position) {
    this.sections = rite.sections;
    this.page = 0;
    this.anchor = position ?? null;
    this.flow.style.transform = '';
    this.flow.innerHTML = rite.sections.map((section, index) => `<section id="${section.id}" data-section="${escapeHtml(section.title)}" aria-labelledby="${section.id}-title"><h2 class="section-title" id="${section.id}-title"><span class="section-number" aria-hidden="true">${String(index + 1).padStart(2, '0')}</span>${escapeHtml(section.title)}</h2>${section.blocks.map((block, i) => `<p id="${section.id}-b${i}" class="${block.kind}" data-block>${block.html}</p>`).join('')}</section>`).join('');
    window.scrollTo({ top: 0, behavior: 'instant' });
    this.scheduleLayout();
  }

  configure(mode) {
    this.anchor = this.capture();
    this.mode = mode;
    document.body.dataset.layout = mode;
    this.flow.style.transform = '';
    window.scrollTo({ top: 0, behavior: 'instant' });
    this.scheduleLayout();
  }

  scheduleLayout() {
    cancelAnimationFrame(this.pendingLayout);
    this.pendingLayout = requestAnimationFrame(() => this.layout());
  }

  layout() {
    if (!this.sections.length) return;
    const position = this.anchor;
    this.flow.style.transform = '';
    this.width = this.view.clientWidth;
    this.gap = parseFloat(getComputedStyle(this.flow).columnGap) || 48;
    this.stride = this.width + this.gap;
    this.flow.style.setProperty('--page-width', `${this.width}px`);
    this.total = this.mode === 'pages' ? Math.max(1, Math.round((this.flow.scrollWidth + this.gap) / this.stride)) : 1;
    if (position?.id) {
      const target = document.getElementById(position.id);
      if (target && this.flow.contains(target)) {
        if (this.mode === 'pages') {
          const rect = target.getBoundingClientRect();
          this.page = Math.floor((rect.left - this.flow.getBoundingClientRect().left + 2) / this.stride) + (position.offset || 0);
        } else if (position.atStart) {
          window.scrollTo({ top: 0, behavior: 'instant' });
        } else {
          const rect = target.getBoundingClientRect();
          window.scrollTo({ top: window.scrollY + rect.top - scrollInset + rect.height * (position.fraction || 0), behavior: 'instant' });
        }
      }
    }
    this.page = clamp(this.page, 0, this.total - 1);
    this.display();
  }

  display() {
    this.flow.style.transform = this.mode === 'pages' ? `translateX(${-this.page * this.stride}px)` : '';
    this.report();
  }

  turn(delta) {
    if (!this.sections.length) return;
    if (this.mode === 'scroll') {
      window.scrollBy({ top: delta * window.innerHeight * .85, behavior: 'instant' });
      this.report();
      return;
    }
    this.page = clamp(this.page + delta, 0, this.total - 1);
    this.display();
  }

  goTo(id) {
    const target = document.getElementById(id);
    if (!target || !this.flow.contains(target)) return;
    if (this.mode === 'scroll') {
      window.scrollTo({ top: window.scrollY + target.getBoundingClientRect().top - scrollInset, behavior: 'instant' });
    } else {
      const local = target.getBoundingClientRect().left - this.flow.getBoundingClientRect().left;
      this.page = clamp(Math.floor((local + 2) / this.stride), 0, this.total - 1);
    }
    this.display();
    this.view.focus({ preventScroll: true });
  }

  capture() {
    if (!this.sections.length) return null;
    const viewRect = this.view.getBoundingClientRect();
    const blocks = this.flow.querySelectorAll('.section-title, [data-block]');
    for (const element of blocks) {
      if (!element.getClientRects().length) continue;
      const rects = [...element.getClientRects()];
      const visible = rects.some(rect => this.mode === 'pages'
        ? rect.right > viewRect.left + 2 && rect.left < viewRect.right - 2 && rect.bottom > viewRect.top
        : rect.bottom > scrollInset + 2);
      if (visible) {
        const firstPage = Math.floor((rects[0].left - this.flow.getBoundingClientRect().left + 2) / (this.stride || 1));
        return {
          id: element.id,
          offset: this.mode === 'pages' ? Math.max(0, this.page - firstPage) : 0,
          fraction: this.mode === 'scroll' ? clamp((scrollInset - rects[0].top) / rects[0].height, 0, 1) : 0,
          atStart: this.mode === 'scroll' ? window.scrollY < 1 : this.page === 0,
        };
      }
    }
    return { id: this.sections.at(-1).id, offset: 0 };
  }

  report() {
    if (!this.sections.length) return;
    const flowRect = this.flow.getBoundingClientRect();
    let section = this.sections[0];
    for (const candidate of this.sections) {
      const title = document.getElementById(`${candidate.id}-title`);
      if (!title) continue;
      const rect = title.getBoundingClientRect();
      const reached = this.mode === 'pages'
        ? Math.floor((rect.left - flowRect.left + 2) / this.stride) <= this.page
        : rect.top <= scrollInset + 70;
      if (reached) section = candidate;
    }
    this.anchor = this.capture();
    const range = document.documentElement.scrollHeight - window.innerHeight;
    const progress = this.mode === 'pages' ? (this.page + 1) / this.total : range > 0 ? clamp(window.scrollY / range, 0, 1) : 1;
    this.onChange({ page: this.page, total: this.total, section, progress, position: this.anchor, mode: this.mode });
  }
}
