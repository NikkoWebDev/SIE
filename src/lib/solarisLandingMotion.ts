import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

let cleanupFns: Array<() => void> = []

export function initSolarisLanding() {
  if (typeof window === 'undefined') return

  cleanupSolarisLanding()

  const root = document.querySelector('[data-solaris-landing]') as HTMLElement | null
  const stage = document.querySelector('#solaris-stage') as HTMLElement | null
  const logo = document.querySelector('[data-solar-logo-shell]') as HTMLElement | null
  const floatingCta = document.querySelector('[data-floating-cta]') as HTMLElement | null

  if (!root || !stage || !logo) return

  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches

  gsap.set(document.documentElement, { '--journey-progress': 0 })
  gsap.set('.scene', { autoAlpha: 0, y: 28, filter: 'blur(12px)' })
  gsap.set('[data-scene="curtain"]', { autoAlpha: 1, y: 0, filter: 'blur(0px)' })
  gsap.set(logo, { xPercent: -50, yPercent: -50, x: 0, y: 0, scale: 0.82, rotate: 0 })

  if (reduce) {
    gsap.set('.scene', { autoAlpha: 1, y: 0, filter: 'none' })
    floatingCta?.classList.add('is-visible')
    return
  }

  const mm = gsap.matchMedia()

  mm.add('(min-width: 769px)', () => {
    const tl = gsap.timeline({
      defaults: { ease: 'none' },
      scrollTrigger: {
        trigger: root,
        start: 'top top',
        end: 'bottom bottom',
        scrub: 1.05,
        pin: stage,
        anticipatePin: 1,
      },
    })

    tl.to(document.documentElement, { '--journey-progress': 1, duration: 1 }, 0)
      .to('[data-scene="curtain"]', { autoAlpha: 0, y: -24, filter: 'blur(16px)', duration: 0.08 }, 0.04)
      .to(logo, { scale: 1.18, duration: 0.13 }, 0.04)
      .to('[data-scene="hero"]', { autoAlpha: 1, y: 0, filter: 'blur(0px)', duration: 0.12 }, 0.10)
      .to('[data-scene="hero"]', { autoAlpha: 0, y: -30, filter: 'blur(14px)', duration: 0.10 }, 0.22)
      .to(logo, { x: '-27vw', y: '0vh', scale: 0.80, rotate: -18, duration: 0.15 }, 0.22)
      .to('[data-scene="stats"]', { autoAlpha: 1, y: 0, filter: 'blur(0px)', duration: 0.12 }, 0.27)
      .from('.stat-card', { y: 28, autoAlpha: 0, stagger: 0.025, duration: 0.10 }, 0.29)
      .to('[data-scene="stats"]', { autoAlpha: 0, y: -26, filter: 'blur(14px)', duration: 0.10 }, 0.40)
      .to(logo, { x: '0vw', y: '-26vh', scale: 0.68, rotate: 22, duration: 0.14 }, 0.40)
      .to('[data-scene="features"]', { autoAlpha: 1, y: 0, filter: 'blur(0px)', duration: 0.12 }, 0.45)
      .from('.feature-card', { y: 30, autoAlpha: 0, stagger: 0.035, duration: 0.12 }, 0.47)
      .to('[data-scene="features"]', { autoAlpha: 0, y: -26, filter: 'blur(14px)', duration: 0.10 }, 0.58)
      .to(logo, { x: '0vw', y: '-2vh', scale: 1.08, rotate: -8, duration: 0.14 }, 0.58)
      .to('[data-scene="notices"]', { autoAlpha: 1, y: 0, filter: 'blur(0px)', duration: 0.12 }, 0.63)
      .from('.notice-card', { y: 30, autoAlpha: 0, stagger: 0.035, duration: 0.12 }, 0.65)
      .to('[data-scene="notices"]', { autoAlpha: 0, y: -26, filter: 'blur(14px)', duration: 0.10 }, 0.77)
      .to(logo, { x: '0vw', y: '-34vh', scale: 0.72, rotate: 0, duration: 0.16 }, 0.77)
      .to('[data-scene="cta"]', { autoAlpha: 1, y: 0, filter: 'blur(0px)', duration: 0.15 }, 0.82)

    cleanupFns.push(() => tl.kill())
  })

  mm.add('(max-width: 768px)', () => {
    const tl = gsap.timeline({
      defaults: { ease: 'none' },
      scrollTrigger: {
        trigger: root,
        start: 'top top',
        end: 'bottom bottom',
        scrub: 0.85,
        pin: stage,
        anticipatePin: 1,
      },
    })

    tl.to(document.documentElement, { '--journey-progress': 1, duration: 1 }, 0)
      .to('[data-scene="curtain"]', { autoAlpha: 0, y: -18, filter: 'blur(10px)', duration: 0.08 }, 0.04)
      .to(logo, { scale: 0.82, y: '-24vh', duration: 0.18 }, 0.06)
      .to('[data-scene="hero"]', { autoAlpha: 1, y: 0, filter: 'blur(0px)', duration: 0.14 }, 0.12)
      .to('[data-scene="hero"]', { autoAlpha: 0, y: -20, filter: 'blur(10px)', duration: 0.10 }, 0.30)
      .to('[data-scene="stats"]', { autoAlpha: 1, y: 0, filter: 'blur(0px)', duration: 0.14 }, 0.36)
      .to('[data-scene="stats"]', { autoAlpha: 0, y: -20, filter: 'blur(10px)', duration: 0.10 }, 0.52)
      .to('[data-scene="features"]', { autoAlpha: 1, y: 0, filter: 'blur(0px)', duration: 0.14 }, 0.58)
      .to('[data-scene="features"]', { autoAlpha: 0, y: -20, filter: 'blur(10px)', duration: 0.10 }, 0.70)
      .to('[data-scene="cta"]', { autoAlpha: 1, y: 0, filter: 'blur(0px)', duration: 0.16 }, 0.78)
      .to(logo, { y: '-34vh', scale: 0.62, duration: 0.30 }, 0.70)

    cleanupFns.push(() => tl.kill())
  })

  const ctaTrigger = ScrollTrigger.create({
    trigger: root,
    start: '12% top',
    end: 'bottom bottom',
    onEnter: () => floatingCta?.classList.add('is-visible'),
    onLeaveBack: () => floatingCta?.classList.remove('is-visible'),
  })

  cleanupFns.push(() => ctaTrigger.kill())
  cleanupFns.push(() => mm.revert())

  const beforeSwap = () => cleanupSolarisLanding()
  window.addEventListener('beforeunload', beforeSwap)
  document.addEventListener('astro:before-swap', beforeSwap)
  cleanupFns.push(() => window.removeEventListener('beforeunload', beforeSwap))
  cleanupFns.push(() => document.removeEventListener('astro:before-swap', beforeSwap))
}

export function cleanupSolarisLanding() {
  cleanupFns.forEach((fn) => fn())
  cleanupFns = []
}
