export interface UnsplashImage {
  url: string;
  alt: string;
  credit: string;
}

export const HERO_IMAGE: UnsplashImage = {
  url: "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=1920&q=80",
  alt: "Call center agent with headset at workstation",
  credit: "John Schnobrich / Unsplash",
};

export const GALLERY_IMAGES: UnsplashImage[] = [
  {
    url: "https://images.unsplash.com/photo-1521737604893-d14cc237f11d?w=1200&q=80",
    alt: "Team collaborating around laptops",
    credit: "Marvin Meyer / Unsplash",
  },
  {
    url: "https://images.unsplash.com/photo-1531482615713-2afd69097998?w=1200&q=80",
    alt: "Support agent helping customer",
    credit: "Redd / Unsplash",
  },
  {
    url: "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=1200&q=80",
    alt: "Professional woman at computer with headset",
    credit: "LinkedIn Sales Solutions / Unsplash",
  },
  {
    url: "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=1200&q=80",
    alt: "Data dashboard analytics screen",
    credit: "Luke Chesser / Unsplash",
  },
  {
    url: "https://images.unsplash.com/photo-1677442135703-1787eea5ce01?w=1200&q=80",
    alt: "AI neural network visualization",
    credit: "Resource Database / Unsplash",
  },
  {
    url: "https://images.unsplash.com/photo-1600880292203-757bb62b4baf?w=1200&q=80",
    alt: "Modern open office with natural light",
    credit: "Campaign Creators / Unsplash",
  },
];

export const PAIN_IMAGE: UnsplashImage = {
  url: "https://images.unsplash.com/photo-1586473219010-2ffc57b0d282?w=1200&q=80",
  alt: "Frustrated person at computer",
  credit: "Elisa Ventur / Unsplash",
};

export const CTA_IMAGE: UnsplashImage = {
  url: "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=1920&q=80",
  alt: "Data visualization on screen",
  credit: "Carlos Muza / Unsplash",
};
