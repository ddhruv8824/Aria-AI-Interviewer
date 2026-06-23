import * as React from "react"

const MOBILE_BREAKPOINT = 768

export function useIsMobile() {
  const [isMobile, setIsMobile] = React.useState<boolean | undefined>(undefined)

  React.useEffect(() => {
    const mql = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT - 1}px)`)
    const onChange = () => setIsMobile(window.innerWidth < MOBILE_BREAKPOINT)
    mql.addEventListener("change", onChange)
    
    // Only set if different from initial layout state to avoid synchronous react-hooks triggers
    // though typically the initial state should be populated differently.
    // It's safe to set it inside the handler but let's just use onChange initially:
    setIsMobile(mql.matches)
    
    return () => mql.removeEventListener("change", onChange)
  }, [])

  return !!isMobile
}
