"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { useMotion } from "@/components/motion";

export function ScrollReset() {
  const pathname = usePathname();
  const { scrollTo } = useMotion();

  useEffect(() => {
    scrollTo(0);
  }, [pathname, scrollTo]);

  return null;
}
