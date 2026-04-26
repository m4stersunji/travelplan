import { Outlet, createRootRoute } from "@tanstack/react-router";
import { NavDesktop } from "@/components/nav-desktop";
import { NavMobile } from "@/components/nav-mobile";

export const Route = createRootRoute({
  component: RootLayout,
});

function RootLayout() {
  return (
    <div className="min-h-screen flex flex-col">
      <NavDesktop />
      <main className="flex-1 mx-auto w-full max-w-2xl px-4 py-4 md:py-8 pb-24 md:pb-8">
        <Outlet />
      </main>
      <NavMobile />
    </div>
  );
}
