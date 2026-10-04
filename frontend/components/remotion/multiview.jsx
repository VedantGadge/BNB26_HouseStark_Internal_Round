"use client";
import { useEffect, useRef, useState } from "react";
import { Player } from "@remotion/player";
import { Img, interpolate, useCurrentFrame } from "remotion";
import { Pause, Play } from "@phosphor-icons/react";

function MultiviewScene() {
  const frame = useCurrentFrame();
  return <div style={{ width:1280,height:390,position:"relative" }}>
    <div style={{ position:"absolute",left:0,top:0,width:218,height:390,borderRadius:14,overflow:"hidden",background:"#17171a" }}>
      <Img src="/media/coastline.webp" style={{ width:"100%",height:"100%",objectFit:"cover",scale:interpolate(frame,[0,240],[1,1.025],{extrapolateRight:"clamp"}) }} />
      <div style={{ position:"absolute",left:18,right:18,bottom:38,color:"white",fontSize:20,fontWeight:600,textAlign:"center",textShadow:"0 2px 6px rgba(0,0,0,.7)",lineHeight:1.3 }}>Make room for<br/>a new perspective.</div>
    </div>
    <div style={{ position:"absolute",left:232,top:0,width:710,height:390,borderRadius:14,overflow:"hidden",background:"#17171a" }}>
      <Img src="/media/coastline.webp" style={{ width:"100%",height:"100%",objectFit:"cover",scale:interpolate(frame,[0,240],[1,1.025],{extrapolateRight:"clamp"}) }} />
      <div style={{ position:"absolute",left:30,right:30,bottom:25,color:"white",fontSize:29,fontWeight:600,textAlign:"center",textShadow:"0 2px 6px rgba(0,0,0,.7)" }}>Make room for a new perspective.</div>
    </div>
    <div style={{ position:"absolute",left:956,top:0,width:324,height:324,borderRadius:14,overflow:"hidden",background:"#17171a" }}>
      <Img src="/media/coastline.webp" style={{ width:"100%",height:"100%",objectFit:"cover",objectPosition:"75% center",scale:interpolate(frame,[0,240],[1,1.025],{extrapolateRight:"clamp"}) }} />
    </div>
  </div>;
}

export default function Multiview() {
  const player = useRef(null);
  const [frame,setFrame] = useState(0),[playing,setPlaying] = useState(false);
  useEffect(() => {
    const ref=player.current;
    if(!ref)return;
    const update=(event)=>setFrame(event.detail.frame);
    const play=()=>setPlaying(true), pause=()=>setPlaying(false);
    ref.addEventListener("frameupdate",update); ref.addEventListener("play",play);ref.addEventListener("pause",pause);
    return()=>{ref.removeEventListener("frameupdate",update);ref.removeEventListener("play",play);ref.removeEventListener("pause",pause);};
  },[]);
  return <div className="multiview-tray">
    <Player ref={player} component={MultiviewScene} durationInFrames={240} compositionWidth={1280} compositionHeight={390} fps={30} style={{width:"100%",borderRadius:14}} loop controls={false} acknowledgeRemotionLicense />
    <div className="demo-controls"><button aria-label={playing?"Pause illustrative preview":"Play illustrative preview"} onClick={()=>player.current?.toggle()}>{playing?<Pause weight="light" size={18}/>:<Play weight="light" size={18}/>}</button><span>Illustrative preview</span>
      <input type="range" min="0" max="239" value={frame} aria-label="Illustrative preview position" onChange={(event)=>player.current?.seekTo(Number(event.target.value))}/><span className="duration-label">{(frame/30).toFixed(1)}s / 8s</span>
    </div>
  </div>;
}
