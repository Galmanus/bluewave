import { useState } from "react";
import { ImageIcon, VideoIcon } from "lucide-react";
import { getAssetFileUrl } from "../hooks/useAssets";

interface Props {
  assetId: string;
  fileType: string;
  className?: string;
}

export default function AssetThumbnail({ assetId, fileType, className = "" }: Props) {
  const [error, setError] = useState(false);
  const isVideo = fileType.startsWith("video/");

  if (error || isVideo) {
    const Icon = isVideo ? VideoIcon : ImageIcon;
    return (
      <div className={`flex items-center justify-center bg-gray-100 dark:bg-gray-800 ${className}`}>
        <Icon className="w-8 h-8 text-gray-400" />
      </div>
    );
  }

  // Use the thumbnail endpoint via proxy (auth via cookie/interceptor)
  const src = `/api/v1/assets/${assetId}/thumbnail`;

  return (
    <img
      src={src}
      alt=""
      loading="lazy"
      className={`object-cover ${className}`}
      onError={() => setError(true)}
    />
  );
}
