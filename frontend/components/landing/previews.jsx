"use client";
import dynamic from "next/dynamic";
import { useState } from "react";
import Image from "next/image";
import { CheckCircle, Copy } from "@phosphor-icons/react";

export const HeroPreview = dynamic(()=>import("@/components/remotion/multiview"),{ssr:false,loading:()=> <div className="multiview-tray" style={{aspectRatio:"1280 / 435"}}><div className="multiview-layout"><div className="demo-frame portrait"><Image src="/media/coastline.webp" fill sizes="20vw" alt="Illustrative creator filming a Mediterranean coastline" priority/></div><div className="demo-center"><div className="demo-frame landscape"><Image src="/media/coastline.webp" fill sizes="55vw" alt="" priority/></div><span className="muted">Illustrative preview</span></div><div className="demo-frame square"><Image src="/media/coastline.webp" fill sizes="25vw" alt="" /></div></div></div>});

export function EditDemo() {
  const [caption,setCaption]=useState("Make room for a new perspective.");
  const [saved,setSaved]=useState(null);
  return <div className="edit-demo"><div className="edit-demo-header"><strong>Coastline story</strong><span>Illustrative edit</span></div>
    <div className="demo-frame"><Image src="/media/coastline.webp" fill sizes="(max-width:800px) 90vw, 50vw" alt="Illustrative source photo of a creator filming the sea"/><p className="demo-caption">{caption}</p></div>
    <label className="field"><span>Try a caption</span><textarea maxLength={120} value={caption} onChange={(event)=>setCaption(event.target.value)}/></label>
    <button type="button" className="button" disabled={!caption.trim()} onClick={()=>setSaved(caption)}><Copy weight="light" size={17}/>Save demo version</button>
    <footer aria-live="polite">{saved?<><CheckCircle size={18} weight="light"/><span>Demo version saved. Original stays untouched.</span></>:<span>Try the edit. Your demo changes stay on this page.</span>}</footer>
    {saved && <p className="muted" style={{fontSize:13,margin:"10px 0 0"}}>Saved caption: {saved}</p>}
  </div>;
}
