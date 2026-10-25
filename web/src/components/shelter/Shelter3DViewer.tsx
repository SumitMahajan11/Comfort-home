"use client";

import React, { useEffect, useRef, useState } from "react";
import { DesignVariables } from "@/types";
import { Compass, RotateCcw, Eye, Layers } from "lucide-react";

interface Shelter3DViewerProps {
  design: DesignVariables;
  className?: string;
  showLabels?: boolean;
}

export const Shelter3DViewer: React.FC<Shelter3DViewerProps> = ({
  design,
  className = "",
  showLabels = true
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [rotationAngle, setRotationAngle] = useState<number>(35); // user interactive drag angle
  const [pitchAngle, setPitchAngle] = useState<number>(25);
  const isDraggingRef = useRef<boolean>(false);
  const lastMousePosRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  // Mouse drag interaction
  const handleMouseDown = (e: React.MouseEvent) => {
    isDraggingRef.current = true;
    lastMousePosRef.current = { x: e.clientX, y: e.clientY };
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDraggingRef.current) return;
    const dx = e.clientX - lastMousePosRef.current.x;
    const dy = e.clientY - lastMousePosRef.current.y;
    setRotationAngle((prev) => (prev + dx * 0.5) % 360);
    setPitchAngle((prev) => Math.max(10, Math.min(65, prev - dy * 0.4)));
    lastMousePosRef.current = { x: e.clientX, y: e.clientY };
  };

  const handleMouseUp = () => {
    isDraggingRef.current = false;
  };

  const resetView = () => {
    setRotationAngle(35);
    setPitchAngle(25);
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Handle high DPI
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const width = rect.width;
    const height = rect.height;
    ctx.clearRect(0, 0, width, height);

    // Center coordinates
    const cx = width / 2;
    const cy = height / 2 + 20;

    // Shelter base dimensions in pixels
    const shelterL = 160; // Length (X)
    const shelterW = 120; // Width (Y)
    const shelterH = 80;  // Height (Z)

    // Orientation angle combined with user orbit
    const netAngleRad = ((rotationAngle + design.orientation) * Math.PI) / 180;
    const pitchRad = (pitchAngle * Math.PI) / 180;

    // 3D Isometric projection helper
    const project = (x: number, y: number, z: number): [number, number] => {
      // Rotate around Z axis (orientation + view)
      const rotX = x * Math.cos(netAngleRad) - y * Math.sin(netAngleRad);
      const rotY = x * Math.sin(netAngleRad) + y * Math.cos(netAngleRad);
      // Project with pitch
      const screenX = cx + rotX;
      const screenY = cy + rotY * Math.sin(pitchRad) - z * Math.cos(pitchRad);
      return [screenX, screenY];
    };

    // Draw Ground Shadow
    ctx.beginPath();
    const gP1 = project(-shelterL / 2 - 15, -shelterW / 2 - 15, 0);
    const gP2 = project(shelterL / 2 + 15, -shelterW / 2 - 15, 0);
    const gP3 = project(shelterL / 2 + 15, shelterW / 2 + 15, 0);
    const gP4 = project(-shelterL / 2 - 15, shelterW / 2 + 15, 0);
    ctx.moveTo(gP1[0], gP1[1]);
    ctx.lineTo(gP2[0], gP2[1]);
    ctx.lineTo(gP3[0], gP3[1]);
    ctx.lineTo(gP4[0], gP4[1]);
    ctx.closePath();
    ctx.fillStyle = "rgba(0, 0, 0, 0.25)";
    ctx.fill();

    // Wall Colors based on Wall Mass Class
    let wallFill = "#D97706"; // Medium clay brick default
    let wallStroke = "#B45309";
    if (design.wall_mass_class === "light") {
      wallFill = "#E2E8F0"; // Light timber/sheet
      wallStroke = "#94A3B8";
    } else if (design.wall_mass_class === "heavy") {
      wallFill = "#64748B"; // Heavy concrete
      wallStroke = "#334155";
    }

    // Roof color based on Roof Solar Absorptance (0.3 = Cool white, 0.9 = Dark bitumen)
    const absorpRatio = (design.roof_solar_absorptance - 0.3) / 0.6;
    const rShade = Math.round(245 - absorpRatio * 180);
    const gShade = Math.round(245 - absorpRatio * 180);
    const bShade = Math.round(245 - absorpRatio * 170);
    const roofFill = `rgb(${rShade}, ${gShade}, ${bShade})`;

    // Draw South & West Walls
    const corners = [
      project(-shelterL / 2, -shelterW / 2, 0),        // 0: Bottom-rear-left
      project(shelterL / 2, -shelterW / 2, 0),         // 1: Bottom-rear-right
      project(shelterL / 2, shelterW / 2, 0),          // 2: Bottom-front-right
      project(-shelterL / 2, shelterW / 2, 0),         // 3: Bottom-front-left
      project(-shelterL / 2, -shelterW / 2, shelterH), // 4: Top-rear-left
      project(shelterL / 2, -shelterW / 2, shelterH),  // 5: Top-rear-right
      project(shelterL / 2, shelterW / 2, shelterH),   // 6: Top-front-right
      project(-shelterL / 2, shelterW / 2, shelterH),  // 7: Top-front-left
    ];

    // Wall Front (face 3-2-6-7)
    ctx.beginPath();
    ctx.moveTo(corners[3][0], corners[3][1]);
    ctx.lineTo(corners[2][0], corners[2][1]);
    ctx.lineTo(corners[6][0], corners[6][1]);
    ctx.lineTo(corners[7][0], corners[7][1]);
    ctx.closePath();
    ctx.fillStyle = wallFill;
    ctx.fill();
    ctx.strokeStyle = wallStroke;
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Wall Right (face 2-1-5-6)
    ctx.beginPath();
    ctx.moveTo(corners[2][0], corners[2][1]);
    ctx.lineTo(corners[1][0], corners[1][1]);
    ctx.lineTo(corners[5][0], corners[5][1]);
    ctx.lineTo(corners[6][0], corners[6][1]);
    ctx.closePath();
    ctx.fillStyle = design.wall_mass_class === "light" ? "#CBD5E1" : (design.wall_mass_class === "heavy" ? "#475569" : "#B45309");
    ctx.fill();
    ctx.stroke();

    // Window on Front Wall scaled by WWR (5% - 40%)
    const wwrRatio = Math.max(0.05, Math.min(0.40, design.wwr / 100));
    const winWidth = (shelterL * 0.7) * (wwrRatio / 0.35);
    const winHeight = (shelterH * 0.6) * Math.sqrt(wwrRatio / 0.2);
    const winBottom = 20;

    const wP1 = project(-winWidth / 2, shelterW / 2 + 0.5, winBottom);
    const wP2 = project(winWidth / 2, shelterW / 2 + 0.5, winBottom);
    const wP3 = project(winWidth / 2, shelterW / 2 + 0.5, winBottom + winHeight);
    const wP4 = project(-winWidth / 2, shelterW / 2 + 0.5, winBottom + winHeight);

    ctx.beginPath();
    ctx.moveTo(wP1[0], wP1[1]);
    ctx.lineTo(wP2[0], wP2[1]);
    ctx.lineTo(wP3[0], wP3[1]);
    ctx.lineTo(wP4[0], wP4[1]);
    ctx.closePath();
    ctx.fillStyle = "rgba(56, 189, 248, 0.75)"; // Glazing blue
    ctx.fill();
    ctx.strokeStyle = "#0284C7";
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Window Mullions (glazing grid)
    ctx.beginPath();
    const wMidBottom = project(0, shelterW / 2 + 0.5, winBottom);
    const wMidTop = project(0, shelterW / 2 + 0.5, winBottom + winHeight);
    ctx.moveTo(wMidBottom[0], wMidBottom[1]);
    ctx.lineTo(wMidTop[0], wMidTop[1]);
    ctx.stroke();

    // Overhang Shading Projection (0.0 - 1.0 m)
    const shadePx = design.shading_depth * 28; // scale to canvas
    if (shadePx > 1) {
      const sP1 = project(-winWidth / 2 - 8, shelterW / 2 + 0.5, winBottom + winHeight + 2);
      const sP2 = project(winWidth / 2 + 8, shelterW / 2 + 0.5, winBottom + winHeight + 2);
      const sP3 = project(winWidth / 2 + 8, shelterW / 2 + shadePx, winBottom + winHeight + 2);
      const sP4 = project(-winWidth / 2 - 8, shelterW / 2 + shadePx, winBottom + winHeight + 2);

      ctx.beginPath();
      ctx.moveTo(sP1[0], sP1[1]);
      ctx.lineTo(sP2[0], sP2[1]);
      ctx.lineTo(sP3[0], sP3[1]);
      ctx.lineTo(sP4[0], sP4[1]);
      ctx.closePath();
      ctx.fillStyle = "rgba(71, 85, 105, 0.95)";
      ctx.fill();
      ctx.strokeStyle = "#1E293B";
      ctx.stroke();
    }

    // Roof Slab (face 7-6-5-4)
    ctx.beginPath();
    ctx.moveTo(corners[7][0], corners[7][1]);
    ctx.lineTo(corners[6][0], corners[6][1]);
    ctx.lineTo(corners[5][0], corners[5][1]);
    ctx.lineTo(corners[4][0], corners[4][1]);
    ctx.closePath();
    ctx.fillStyle = roofFill;
    ctx.fill();
    ctx.strokeStyle = "#334155";
    ctx.lineWidth = 2;
    ctx.stroke();

    // Roof Solar Reflectance Glow / Indicator
    if (design.roof_solar_absorptance <= 0.4) {
      ctx.save();
      ctx.shadowColor = "rgba(56, 189, 248, 0.4)";
      ctx.shadowBlur = 10;
      ctx.strokeStyle = "rgba(56, 189, 248, 0.8)";
      ctx.stroke();
      ctx.restore();
    }

    // Ventilation indicator arrows if ventilation > 8 ACH
    if (design.ventilation_ach >= 6.0) {
      const vP1 = project(-shelterL / 2 - 25, shelterW / 4, shelterH * 0.4);
      const vP2 = project(-shelterL / 2 - 5, shelterW / 4, shelterH * 0.4);
      ctx.beginPath();
      ctx.moveTo(vP1[0], vP1[1]);
      ctx.lineTo(vP2[0], vP2[1]);
      ctx.strokeStyle = "rgba(42, 127, 142, 0.85)";
      ctx.lineWidth = 2.5;
      ctx.setLineDash([4, 4]);
      ctx.stroke();
      ctx.setLineDash([]);
    }
  }, [design, rotationAngle, pitchAngle]);

  return (
    <div className={`relative flex flex-col items-center justify-center rounded-2xl glass-panel p-4 ${className}`}>
      {/* 3D Canvas */}
      <canvas
        ref={canvasRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        className="w-full h-64 md:h-72 cursor-grab active:cursor-grabbing rounded-xl"
        title="Click and drag to rotate 3D shelter view"
      />

      {/* Floating View Controls & Orientation Gauge */}
      <div className="absolute top-4 right-4 flex items-center space-x-2">
        <button
          onClick={resetView}
          className="p-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white transition shadow border border-slate-700/60"
          title="Reset 3D camera angle"
        >
          <RotateCcw className="w-4 h-4" />
        </button>
      </div>

      {/* Orientation Indicator */}
      <div className="absolute top-4 left-4 flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-slate-900/80 border border-slate-700/60 text-xs font-mono text-teal-400">
        <Compass className="w-3.5 h-3.5 text-teal-400" />
        <span>{design.orientation}° Azimuth</span>
      </div>

      {/* Interactive Labels & Badges */}
      {showLabels && (
        <div className="w-full mt-3 grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
          <div className="p-2 rounded-lg bg-slate-800/60 border border-slate-700/40">
            <span className="text-slate-400 block text-[10px]">Roof Absorptance</span>
            <span className="font-semibold text-slate-200">
              {design.roof_solar_absorptance.toFixed(2)} ({design.roof_solar_absorptance <= 0.4 ? "Cool White" : "Standard"})
            </span>
          </div>
          <div className="p-2 rounded-lg bg-slate-800/60 border border-slate-700/40">
            <span className="text-slate-400 block text-[10px]">Glazing WWR</span>
            <span className="font-semibold text-slate-200">{design.wwr}% Wall Area</span>
          </div>
          <div className="p-2 rounded-lg bg-slate-800/60 border border-slate-700/40">
            <span className="text-slate-400 block text-[10px]">Overhang Shading</span>
            <span className="font-semibold text-slate-200">{design.shading_depth.toFixed(2)} m</span>
          </div>
          <div className="p-2 rounded-lg bg-slate-800/60 border border-slate-700/40">
            <span className="text-slate-400 block text-[10px]">Wall Material</span>
            <span className="font-semibold text-slate-200 capitalize">{design.wall_mass_class} Mass</span>
          </div>
        </div>
      )}
    </div>
  );
};
