import { forwardRef, useId } from "react"
import { OTPInput, OTPInputContext } from "input-otp"
import { cn } from "@/lib/utils"
import { Dot } from "lucide-react"

const OTPInputGroup = forwardRef<
  React.ElementRef<typeof OTPInput>,
  React.ComponentPropsWithoutRef<typeof OTPInput>
>(({ className, ...props }, ref) => {
  const id = useId()

  return (
    <OTPInput
      ref={ref}
      containerClassName={cn(
        "flex items-center gap-2 has-[:disabled]:opacity-50",
        className
      )}
      {...props}
    />
  )
})
OTPInputGroup.displayName = "OTPInputGroup"

const OTPInputSlot = forwardRef<
  React.ElementRef<"div">,
  React.ComponentPropsWithoutRef<"div"> & { index: number }
>(({ index, className, ...props }, ref) => {
  const inputClassName = cn(
    "w-10 h-12 text-center text-2xl font-semibold border rounded-md focus:border-primary focus:ring-1 focus:ring-primary",
    className
  )

  return (
    <div
      ref={ref}
      className={cn("relative w-10 h-12", className)}
      {...props}
    >
      <OTPInputContext.Slot
        index={index}
        className={inputClassName}
      />
    </div>
  )
})
OTPInputSlot.displayName = "OTPInputSlot"

const OTPInputSeparator = ({ ...props }) => {
  return (
    <div role="separator" {...props}>
      <Dot className="w-4 h-4" />
    </div>
  )
}
OTPInputSeparator.displayName = "OTPInputSeparator"

export { OTPInputGroup, OTPInputSlot, OTPInputSeparator }
