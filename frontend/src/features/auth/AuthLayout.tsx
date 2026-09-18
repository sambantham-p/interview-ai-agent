import { Link } from 'react-router'
import { PrepwiseLogo } from '../../components/ui/PrepwiseLogo'
import { ShieldCheckIcon } from '../../components/ui/ShieldCheckIcon'

interface AuthLayoutProps {
  children: React.ReactNode
}

export function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <div className="min-h-screen w-full flex flex-col lg:flex-row bg-[#f4f7fa]">
      {/* Left Product Story Panel from Figma (Node 7:459) */}
      <div className="w-full lg:w-130 xl:w-140 bg-[#0b1625] text-white p-8 lg:p-14 flex flex-col justify-between shrink-0 select-none">
        {/* Brand Lockup - doubles as "back to home", the conventional
            place users expect that on an auth page, so it doesn't need
            its own separate back button/link taking up form space. */}
        <div>
          <Link
            to="/"
            className="inline-block rounded-md transition-opacity hover:opacity-80 focus-visible:outline focus-visible:outline-brand focus-visible:outline-offset-4"
            aria-label="Back to home"
          >
            <PrepwiseLogo variant="dark" size="md" />
          </Link>
        </div>

        {/* Promise Section */}
        <div className="my-10 lg:my-0 flex flex-col gap-6 max-w-md">
          {/* Trust badge */}
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#18314d] border border-[#18314d] w-fit">
            <span
              className="text-[11px] font-semibold tracking-wider text-faint"
            >
              PRIVATE • STRUCTURED • ACTIONABLE
            </span>
          </div>

          {/* Headline */}
          <h1
            className="text-3xl lg:text-[36px] font-normal leading-[1.18] text-white"
          >
            Practice with purpose. <br />
            Interview with confidence.
          </h1>

          {/* Description */}
          <p
            className="text-[15px] lg:text-[16px] text-hairline leading-relaxed font-normal"
          >
            Five focused interview phases, from background to career fit, followed by a clear AI-generated evaluation.
          </p>
        </div>

        {/* Privacy Note */}
        <div className="flex items-center gap-2.5 text-hairline text-[13px]">
          <ShieldCheckIcon className="w-4 h-4 text-brand" />
          <span>Your resume and interview data stay protected.</span>
        </div>
      </div>

      {/* Right Form Area from Figma (Node 7:472) */}
      <div className="flex-1 flex items-center justify-center p-6 sm:p-10 lg:p-16">
        <div className="w-full max-w-110 bg-white rounded-2xl shadow-sm border border-[#e2e8f0] p-7 sm:p-10">
          {children}
        </div>
      </div>
    </div>
  )
}
