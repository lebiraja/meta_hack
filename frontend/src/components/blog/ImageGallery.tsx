"use client";
import { useCallback, useEffect, useState } from "react";
import useEmblaCarousel from "embla-carousel-react";
import Autoplay from "embla-carousel-autoplay";
import Image from "next/image";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { motion } from "framer-motion";
import { GALLERY_IMAGES } from "@/lib/unsplash";
import { fadeIn, viewportOnce } from "@/lib/motion";

export function ImageGallery() {
  const [emblaRef, emblaApi] = useEmblaCarousel({ loop: true, align: "center" }, [
    Autoplay({ delay: 3500, stopOnInteraction: false }),
  ]);
  const [selectedIndex, setSelectedIndex] = useState(0);

  const onSelect = useCallback(() => {
    if (!emblaApi) return;
    setSelectedIndex(emblaApi.selectedScrollSnap());
  }, [emblaApi]);

  useEffect(() => {
    if (!emblaApi) return;
    emblaApi.on("select", onSelect);
    onSelect();
  }, [emblaApi, onSelect]);

  return (
    <motion.section
      variants={fadeIn}
      initial="hidden"
      whileInView="visible"
      viewport={viewportOnce}
      className="relative overflow-hidden bg-[#060c1a] py-16"
    >
      <div className="relative">
        <div ref={emblaRef} className="overflow-hidden">
          <div className="flex gap-4">
            {GALLERY_IMAGES.map((img, i) => (
              <div
                key={i}
                className="relative min-w-0 flex-[0_0_85%] overflow-hidden rounded-2xl md:flex-[0_0_50%] lg:flex-[0_0_33%]"
              >
                <Image
                  src={img.url}
                  alt={img.alt}
                  width={600}
                  height={400}
                  className="h-64 w-full object-cover brightness-75 transition-all duration-500 hover:brightness-90 md:h-80"
                />
                <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-4">
                  <p className="text-xs text-slate-400">{img.credit}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Controls */}
        <button
          onClick={() => emblaApi?.scrollPrev()}
          className="absolute left-4 top-1/2 -translate-y-1/2 rounded-full bg-black/50 p-2 text-white backdrop-blur-sm transition-all hover:bg-black/70"
        >
          <ChevronLeft className="h-5 w-5" />
        </button>
        <button
          onClick={() => emblaApi?.scrollNext()}
          className="absolute right-4 top-1/2 -translate-y-1/2 rounded-full bg-black/50 p-2 text-white backdrop-blur-sm transition-all hover:bg-black/70"
        >
          <ChevronRight className="h-5 w-5" />
        </button>
      </div>

      {/* Dots */}
      <div className="mt-6 flex justify-center gap-2">
        {GALLERY_IMAGES.map((_, i) => (
          <button
            key={i}
            onClick={() => emblaApi?.scrollTo(i)}
            className={`h-1.5 rounded-full transition-all duration-300 ${
              i === selectedIndex ? "w-6 bg-indigo-400" : "w-1.5 bg-slate-600"
            }`}
          />
        ))}
      </div>
    </motion.section>
  );
}
