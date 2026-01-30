"use client";
import { Globe, Ship } from "lucide-react";
import { DiscordLogoIcon } from "@radix-ui/react-icons";
import { AiOutlineOpenAI } from "react-icons/ai";

/**
 *
 * NOTE:
 * This is a placeholder home page. You are encouraged to modify or replace it as needed.
 */
export default function Home() {
	return (
		<div className="h-full overflow-auto flex items-center justify-center p-8">
			<div className="flex flex-col items-center space-y-6">
				{/* Description */}
				<div className="bg-[#173401] text-[#9FE870] flex aspect-square size-12 items-center justify-center rounded-lg">
					<Ship className="size-8" />
				</div>
				<div className="max-w-[70%] text-center text-muted-foreground">
					<p>with Shippable, you vibe code B2B apps that go beyond demo and into production</p>
				</div>

				{/* Links */}
				<div className="flex gap-6 justify-center text-[#173401] text-lg">
					<a href="https://shippable.build" target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 hover:scale-105 transition-transform">
						<Globe className="size-4" />
						shippable.build
					</a>
					<a href="https://discord.gg/WdgtG5QHWe" target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 hover:scale-105 transition-transform">
						<DiscordLogoIcon className="size-4" />
						Discord
					</a>
					<a href="https://chatgpt.com/?q=Read+https%3A%2F%2Fshippable.build+and+give+me+an+overview+of+what+Shippable+is%2C+what+I+can+do+with+it%2C+and+how+to+get+started&hints=search" target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 hover:scale-105 transition-transform">
						<AiOutlineOpenAI className="size-5" />
						ChatGPT
					</a>
				</div>
			</div>
		</div>
	);
}
