"use client";

import type React from "react";
import Link from "next/link";
import Header from "@/components/login_header";
import { useSearchParams } from "next/navigation";
import {
  motion,
  useMotionValue,
  useTransform,
  useAnimation,
} from "framer-motion";
import { useEffect, useState } from "react";
import Image from "next/image";

const fadeIn = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.5 },
};

const staggerContainer = {
  animate: {
    transition: {
      staggerChildren: 0.2,
    },
  },
};

export default function Home() {
  const searchParams = useSearchParams();
  const username = searchParams.get("username");
  const balanceStr = searchParams.get("balance");
  const balance = balanceStr ? parseFloat(balanceStr) : null;

  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const rotateX = useTransform(y, [-100, 100], [30, -30]);
  const rotateY = useTransform(x, [-100, 100], [-30, 30]);

  const controls = useAnimation();

  useEffect(() => {
    const updateDimensions = () => {
      setDimensions({
        width: window.innerWidth,
        height: window.innerHeight,
      });
    };
    updateDimensions();
    window.addEventListener("resize", updateDimensions);
    controls.start("visible");
    return () => window.removeEventListener("resize", updateDimensions);
  }, [controls]);

  function handleMouse(event: React.MouseEvent<HTMLDivElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    x.set(event.clientX - rect.left - rect.width / 2);
    y.set(event.clientY - rect.top - rect.height / 2);
  }

  return (
    <div className="min-h-screen bg-[#FDF6E9] overflow-hidden">
      <Header />
      <main>
      {/* Hero section */}
<section
  className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden"
  onMouseMove={handleMouse}
>
  <motion.div
    className="absolute inset-0"
    style={{ rotateX: rotateX, rotateY: rotateY, perspective: 1000 }}
  />

  <motion.div
    className="relative z-10 text-center"
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.7, delay: 0.3 }}
  >
    {username && (
      <h2 className="text-3xl font-bold text-gray-900 mb-4">
        Welcome back, {username}!
      </h2>
    )}
    <h1 className="text-5xl font-bold text-gray-900 mb-6">
      No cash. No touch. No delay.
    </h1>
    <p className="text-xl text-gray-600 mb-8">
      Contactless payment using Facial biometric authentication enables
      secure,<br />
      biometric authentication by allowing users to authorize
      transactions simply by scanning their face.
    </p>
    <div className="relative z-10 text-center mt-8">
      <Link href="/predict">
        <button className="px-6 py-3 bg-blue-600 text-white rounded hover:bg-blue-700">
          Predict
        </button>
      </Link>
    </div>
  </motion.div>
</section>

        {/* Core Features */}
        <section className="py-16 bg-white/50 relative z-10">
          <div className="container mx-auto px-4">
            <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">
              Core Feature
            </h2>
            <motion.div
              className="grid md:grid-cols-3 gap-8 max-w-4xl mx-auto"
              variants={staggerContainer}
              initial="initial"
              whileInView="animate"
              viewport={{ once: true }}
            >
              <motion.div
                className="text-center"
                variants={fadeIn}
                whileHover={{ y: -10 }}
              >
                <div className="flex justify-center items-center">
                  <Image
                    src="/face-id1.png"
                    alt="Face-ID Logo"
                    width={60}
                    height={60}
                  />
                </div>
                <h3 className="text-xl font-semibold mb-2">
                  Seamless Facial Biometric Checkout
                </h3>
                <p className="text-gray-600">
                  Pay instantly using facial recognition (no phones, cards, or
                  cash required.)
                </p>
              </motion.div>
              <motion.div
                className="text-center"
                variants={fadeIn}
                whileHover={{ y: -10 }}
              >
                <div className="flex justify-center items-center">
                  <Image
                    src="/grocery.png"
                    alt="Grocery Logo"
                    width={60}
                    height={60}
                  />
                </div>
                <h3 className="text-xl font-semibold mb-2">
                  Smart Grocery Recognition
                </h3>
                <p className="text-gray-600">
                  AI vision auto-detects grocery items instantly
                </p>
              </motion.div>
              <motion.div
                className="text-center"
                variants={fadeIn}
                whileHover={{ y: -10 }}
              >
                <div className="flex justify-center items-center">
                  <Image
                    src="/insight1.png"
                    alt="Insights Logo"
                    width={60}
                    height={60}
                  />
                </div>
                <h3 className="text-xl font-semibold mb-2">
                  Intelligent Store Insights
                </h3>
                <p className="text-gray-600">
                  Track inventory, customer behavior, and sales in real time
                  with an AI-powered dashboard.
                </p>
              </motion.div>
            </motion.div>
          </div>
        </section>
      </main>

      <footer className="border-t border-neutral-200 py-8 relative z-10">
        <div className="container mx-auto px-4">
          <motion.div
            className="flex flex-col md:flex-row justify-between items-center"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            <p className="text-gray-600 text-sm">
              © {new Date().getFullYear()} Nimbus. All rights reserved.
            </p>
          </motion.div>
        </div>
      </footer>
    </div>
  );
}
