import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

let cleanups: Array<() => void> = []
function reg(fn: () => void) { cleanups.push(fn) }
function kill() {
  cleanups.forEach((fn) => fn())
  cleanups = []
  ScrollTrigger.getAll().forEach((st) => st.kill())
}

export function initLanding() {
  if (typeof window === 'undefined') return
  kill()

  const stage = document.querySelector('[data-landing-stage]') as HTMLElement | null
  const logo = document.querySelector('[data-logo-shell]') as HTMLElement | null
  const fill = document.querySelector('[data-progress-fill]') as HTMLElement | null
  const floatBtn = document.querySelector('[data-float-cta]') as HTMLElement | null
  const cards = gsap.utils.toArray<HTMLElement>('[data-magnetic-card]')
  const magnets = gsap.utils.toArray<HTMLElement>('[data-magnetic]')
  const shifts = gsap.utils.toArray<HTMLElement>('[data-shift]')

  if (!stage || !logo) return

  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches

  gsap.set('[data-scene]', { autoAlpha: 0, y: 22, filter: 'blur(8px)' })
  gsap.set('[data-scene="hero"]', { autoAlpha: 1, y: 0, filter: 'blur(0px)' })

  if (reduced) {
    gsap.set('[data-scene]', { autoAlpha: 1, y: 0, filter: 'none' })
    gsap.set(logo, { xPercent: -50, yPercent: -50, x: 0, y: 0, scale: 1, autoAlpha: 1 })
    floatBtn?.classList.add('is-visible')
    return
  }

  const mm = gsap.matchMedia()

  const build = (o: { x0: string; y0: string; s0: number; sMid: number; xEnd: string; yEnd: string; sEnd: number }) => {
    gsap.set(logo, { xPercent: -50, yPercent: -50, x: o.x0, y: o.y0, scale: o.s0, rotate: -6, autoAlpha: 0.78 })

    const tl = gsap.timeline({
      defaults: { ease: 'none' },
      scrollTrigger: {
        trigger: stage,
        start: 'top top',
        end: '+=320%',
        scrub: 1.1,
        pin: true,
        anticipatePin: 1,
        onUpdate: (self) => { if (fill) fill.style.width = `${self.progress * 100}%` },
      },
    })

    tl.to(logo, { x: 0, y: 0, scale: o.sMid, rotate: 0, autoAlpha: 1, duration: 0.22, ease: 'power3.out' }, 0.04)
      .to('[data-scene="hero"]', { autoAlpha: 0, y: -22, filter: 'blur(10px)', duration: 0.10, ease: 'power1.in' }, 0.30)
      .to(logo, { x: o.xEnd, y: '30vh', scale: 0.6, rotate: 14, autoAlpha: 0.1, duration: 0.16, ease: 'power2.inOut' }, 0.34)
      .to('[data-scene="features"]', { autoAlpha: 1, y: 0, filter: 'blur(0px)', duration: 0.12, ease: 'power2.out' }, 0.44)
      .from(cards, { y: 22, autoAlpha: 0, stagger: 0.05, duration: 0.10, ease: 'power2.out' }, 0.47)
      .to('[data-scene="features"]', { autoAlpha: 0, y: -22, filter: 'blur(10px)', duration: 0.10, ease: 'power1.in' }, 0.70)
      .to(logo, { x: o.xEnd, y: o.yEnd, scale: o.sEnd, rotate: 18, autoAlpha: 0.92, duration: 0.16, ease: 'power3.inOut' }, 0.72)
      .to('[data-scene="cta"]', { autoAlpha: 1, y: 0, filter: 'blur(0px)', duration: 0.16, ease: 'power2.out' }, 0.82)

    reg(() => tl.kill())
  }

  mm.add('(min-width: 769px)', () => {
    build({ x0: '-28vw', y0: '-22vh', s0: 0.66, sMid: 1.2, xEnd: '30vw', yEnd: '28vh', sEnd: 0.66 })
  })
  mm.add('(max-width: 768px)', () => {
    build({ x0: '-14vw', y0: '-26vh', s0: 0.6, sMid: 0.95, xEnd: '16vw', yEnd: '26vh', sEnd: 0.56 })
  })

  const ctaST = ScrollTrigger.create({
    trigger: stage,
    start: 'top top',
    end: '+=320%',
    onUpdate: (self) => {
      if (self.progress > 0.06) floatBtn?.classList.add('is-visible')
      else floatBtn?.classList.remove('is-visible')
    },
  })
  reg(() => ctaST.kill())

  cards.forEach((card) => {
    const xTo = gsap.quickTo(card, 'x', { duration: 0.5, ease: 'power2.out' })
    const yTo = gsap.quickTo(card, 'y', { duration: 0.5, ease: 'power2.out' })
    const onMove = (e: MouseEvent) => {
      const r = card.getBoundingClientRect()
      xTo(((e.clientX - (r.left + r.width / 2)) / (r.width / 2)) * 6)
      yTo(((e.clientY - (r.top + r.height / 2)) / (r.height / 2)) * 4)
    }
    const onLeave = () => { xTo(0); yTo(0) }
    card.addEventListener('mousemove', onMove)
    card.addEventListener('mouseleave', onLeave)
    reg(() => { card.removeEventListener('mousemove', onMove); card.removeEventListener('mouseleave', onLeave) })
  })

  magnets.forEach((el) => {
    const xTo = gsap.quickTo(el, 'x', { duration: 0.45, ease: 'power3.out' })
    const yTo = gsap.quickTo(el, 'y', { duration: 0.45, ease: 'power3.out' })
    const onMove = (e: MouseEvent) => {
      const r = el.getBoundingClientRect()
      xTo((e.clientX - (r.left + r.width / 2)) * 0.3)
      yTo((e.clientY - (r.top + r.height / 2)) * 0.3)
    }
    const onLeave = () => { xTo(0); yTo(0) }
    el.addEventListener('mousemove', onMove)
    el.addEventListener('mouseleave', onLeave)
    reg(() => { el.removeEventListener('mousemove', onMove); el.removeEventListener('mouseleave', onLeave) })
  })

  if (shifts.length) {
    const onScene = gsap.quickTo(shifts, 'y', { duration: 0.6, ease: 'power2.out' })
    reg(() => onScene(0))
  }

  reg(() => mm.revert())
  const onSwap = () => kill()
  document.addEventListener('astro:before-swap', onSwap)
  reg(() => document.removeEventListener('astro:before-swap', onSwap))
}

export { kill as cleanupLanding }
