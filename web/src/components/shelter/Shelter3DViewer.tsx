"use client";

import React, { useEffect, useRef, useState } from "react";
import { DesignVariables } from "@/types";
import { Compass, RotateCcw } from "lucide-react";
import { Badge } from "@/components/ui/Badge";

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
    const cy = height / 2 + 15;

    // Shelter base dimensions in pixels
    const shelterL = 160; // Length (X)
    const shelterW = 120; // Width (Y)
    const shelterH = 80;  // Height (Z)

    // Dynamic thicknesses responding to sliders
    const roofThickPx = 4 + (design.roof_insulation_thickness / 150) * 14; // 4px (uninsulated) to 18px (150 mm)
    const wallThickPx = 2 + (design.wall_insulation_thickness / 150) * 8; // 2px to 10px reveal depth

    // Net orientation angle combined with user orbit
    const netAngleRad = ((rotationAngle + design.orientation) * Math.PI) / 180;
    const pitchRad = (pitchAngle * Math.PI) / 180;

    // 3D Isometric projection helper
    const project = (x: number, y: number, z: number): [number, number] => {
      // Rotate around Z axis (orientation + user orbit)
      const rotX = x * Math.cos(netAngleRad) - y * Math.sin(netAngleRad);
      const rotY = x * Math.sin(netAngleRad) + y * Math.cos(netAngleRad);
      // Project with pitch
      const screenX = cx + rotX;
      const screenY = cy + rotY * Math.sin(pitchRad) - z * Math.cos(pitchRad);
      return [screenX, screenY];
    };

    // 1. Ground Shadow
    ctx.beginPath();
    const gP1 = project(-shelterL / 2 - 16, -shelterW / 2 - 16, 0);
    const gP2 = project(shelterL / 2 + 16, -shelterW / 2 - 16, 0);
    const gP3 = project(shelterL / 2 + 16, shelterW / 2 + 16, 0);
    const gP4 = project(-shelterL / 2 - 16, shelterW / 2 + 16, 0);
    ctx.moveTo(gP1[0], gP1[1]);
    ctx.lineTo(gP2[0], gP2[1]);
    ctx.lineTo(gP3[0], gP3[1]);
    ctx.lineTo(gP4[0], gP4[1]);
    ctx.closePath();
    ctx.fillStyle = "rgba(0, 0, 0, 0.22)";
    ctx.fill();

    // 2. Wall Colors based on Wall Mass Class
    let wallFillFront = "#D97706"; // Medium clay brick default
    let wallFillSide = "#B45309";
    let wallStroke = "#92400E";
    if (design.wall_mass_class === "light") {
      wallFillFront = "#E2E8F0"; // Light timber/sheet
      wallFillSide = "#CBD5E1";
      wallStroke = "#94A3B8";
    } else if (design.wall_mass_class === "heavy") {
      wallFillFront = "#64748B"; // Heavy concrete
      wallFillSide = "#475569";
      wallStroke = "#334155";
    }

    // 3. Roof color based on Roof Solar Absorptance (0.30 = Cool white, 0.90 = Dark bitumen)
    const absorpRatio = Math.max(0, Math.min(1, (design.roof_solar_absorptance - 0.3) / 0.6));
    const rShade = Math.round(245 - absorpRatio * 180);
    const gShade = Math.round(245 - absorpRatio * 180);
    const bShade = Math.round(245 - absorpRatio * 170);
    const roofTopFill = `rgb(${rShade}, ${gShade}, ${bShade})`;
    const roofEdgeFill = `rgb(${Math.max(20, rShade - 40)}, ${Math.max(20, gShade - 40)}, ${Math.max(20, bShade - 40)})`;

    // Base Wall Corners
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
    ctx.fillStyle = wallFillFront;
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
    ctx.fillStyle = wallFillSide;
    ctx.fill();
    ctx.strokeStyle = wallStroke;
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // 4. Window aperture scaled by WWR (5% - 40%) with wall thickness jamb reveal
    const wwrRatio = Math.max(0.05, Math.min(0.40, design.wwr / 100));
    const winWidth = (shelterL * 0.72) * (wwrRatio / 0.35);
    const winHeight = (shelterH * 0.58) * Math.sqrt(wwrRatio / 0.22);
    const winBottom = 20;

    // Window Outer Reveal (Jamb depth proportional to wall insulation thickness)
    const revP1 = project(-winWidth / 2 - wallThickPx, shelterW / 2 + 0.5, winBottom - wallThickPx);
    const revP2 = project(winWidth / 2 + wallThickPx, shelterW / 2 + 0.5, winBottom - wallThickPx);
    const revP3 = project(winWidth / 2 + wallThickPx, shelterW / 2 + 0.5, winBottom + winHeight + wallThickPx);
    const revP4 = project(-winWidth / 2 - wallThickPx, shelterW / 2 + 0.5, winBottom + winHeight + wallThickPx);

    ctx.beginPath();
    ctx.moveTo(revP1[0], revP1[1]);
    ctx.lineTo(revP2[0], revP2[1]);
    ctx.lineTo(revP3[0], revP3[1]);
    ctx.lineTo(revP4[0], revP4[1]);
    ctx.closePath();
    ctx.fillStyle = wallFillSide;
    ctx.fill();
    ctx.strokeStyle = wallStroke;
    ctx.lineWidth = 1;
    ctx.stroke();

    // Glazing pane inset
    const wP1 = project(-winWidth / 2, shelterW / 2 + 0.8, winBottom);
    const wP2 = project(winWidth / 2, shelterW / 2 + 0.8, winBottom);
    const wP3 = project(winWidth / 2, shelterW / 2 + 0.8, winBottom + winHeight);
    const wP4 = project(-winWidth / 2, shelterW / 2 + 0.8, winBottom + winHeight);

    ctx.beginPath();
    ctx.moveTo(wP1[0], wP1[1]);
    ctx.lineTo(wP2[0], wP2[1]);
    ctx.lineTo(wP3[0], wP3[1]);
    ctx.lineTo(wP4[0], wP4[1]);
    ctx.closePath();
    ctx.fillStyle = "rgba(56, 189, 248, 0.82)"; // Glazing blue
    ctx.fill();
    ctx.strokeStyle = "rgba(31, 78, 121, 0.95)";
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Window Mullion
    ctx.beginPath();
    const wMidBottom = project(0, shelterW / 2 + 0.8, winBottom);
    const wMidTop = project(0, shelterW / 2 + 0.8, winBottom + winHeight);
    ctx.moveTo(wMidBottom[0], wMidBottom[1]);
    ctx.lineTo(wMidTop[0], wMidTop[1]);
    ctx.stroke();

    // 5. Overhang Shading Projection (0.0 - 1.0 m)
    const shadePx = design.shading_depth * 32; // scale to canvas
    if (shadePx > 1.5) {
      const sP1 = project(-winWidth / 2 - 10, shelterW / 2 + 0.8, winBottom + winHeight + wallThickPx + 2);
      const sP2 = project(winWidth / 2 + 10, shelterW / 2 + 0.8, winBottom + winHeight + wallThickPx + 2);
      const sP3 = project(winWidth / 2 + 10, shelterW / 2 + shadePx, winBottom + winHeight + wallThickPx + 2);
      const sP4 = project(-winWidth / 2 - 10, shelterW / 2 + shadePx, winBottom + winHeight + wallThickPx + 2);

      ctx.beginPath();
      ctx.moveTo(sP1[0], sP1[1]);
      ctx.lineTo(sP2[0], sP2[1]);
      ctx.lineTo(sP3[0], sP3[1]);
      ctx.lineTo(sP4[0], sP4[1]);
      ctx.closePath();
      ctx.fillStyle = "rgba(51, 65, 85, 0.95)";
      ctx.fill();
      ctx.strokeStyle = "#0F172A";
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }

    // 6. Roof Slab responding to Roof Insulation Thickness (roofThickPx)
    // Roof Top Corners (z = shelterH + roofThickPx) with slight 4px overhang
    const rL = shelterL / 2 + 4;
    const rW = shelterW / 2 + 4;
    const rZBottom = shelterH;
    const rZTop = shelterH + roofThickPx;

    const rTopCorners = [
      project(-rL, -rW, rZTop), // 0: Top-rear-left
      project(rL, -rW, rZTop),  // 1: Top-rear-right
      project(rL, rW, rZTop),   // 2: Top-front-right
      project(-rL, rW, rZTop),  // 3: Top-front-left
    ];

    const rBottomCorners = [
      project(-rL, -rW, rZBottom), // 0: Bottom-rear-left
      project(rL, -rW, rZBottom),  // 1: Bottom-rear-right
      project(rL, rW, rZBottom),   // 2: Bottom-front-right
      project(-rL, rW, rZBottom),  // 3: Bottom-front-left
    ];

    // Roof Front Edge Slab Face
    ctx.beginPath();
    ctx.moveTo(rBottomCorners[3][0], rBottomCorners[3][1]);
    ctx.lineTo(rBottomCorners[2][0], rBottomCorners[2][1]);
    ctx.lineTo(rTopCorners[2][0], rTopCorners[2][1]);
    ctx.lineTo(rTopCorners[3][0], rTopCorners[3][1]);
    ctx.closePath();
    ctx.fillStyle = roofEdgeFill;
    ctx.fill();
    ctx.strokeStyle = "#334155";
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Roof Right Edge Slab Face
    ctx.beginPath();
    ctx.moveTo(rBottomCorners[2][0], rBottomCorners[2][1]);
    ctx.lineTo(rBottomCorners[1][0], rBottomCorners[1][1]);
    ctx.lineTo(rTopCorners[1][0], rTopCorners[1][1]);
    ctx.lineTo(rTopCorners[2][0], rTopCorners[2][1]);
    ctx.closePath();
    ctx.fillStyle = roofEdgeFill;
    ctx.fill();
    ctx.strokeStyle = "#334155";
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Roof Top Slab Face
    ctx.beginPath();
    ctx.moveTo(rTopCorners[3][0], rTopCorners[3][1]);
    ctx.lineTo(rTopCorners[2][0], rTopCorners[2][1]);
    ctx.lineTo(rTopCorners[1][0], rTopCorners[1][1]);
    ctx.lineTo(rTopCorners[0][0], rTopCorners[0][1]);
    ctx.closePath();
    ctx.fillStyle = roofTopFill;
    ctx.fill();
    ctx.strokeStyle = "#1E293B";
    ctx.lineWidth = 2;
    ctx.stroke();

    // Roof Reflectance Glow if high solar reflectance (absorptance <= 0.40)
    if (design.roof_solar_absorptance <= 0.4) {
      ctx.save();
      ctx.shadowColor = "rgba(56, 189, 248, 0.45)";
      ctx.shadowBlur = 12;
      ctx.strokeStyle = "rgba(56, 189, 248, 0.9)";
      ctx.stroke();
      ctx.restore();
    }

    // 7. Ventilation indicator airflow arrows if ventilation rate >= 5.0 ACH
    if (design.ventilation_ach >= 5.0) {
      const vP1 = project(-shelterL / 2 - 28, shelterW / 4, shelterH * 0.45);
      const vP2 = project(-shelterL / 2 - 4, shelterW / 4, shelterH * 0.45);
      ctx.beginPath();
      ctx.moveTo(vP1[0], vP1[1]);
      ctx.lineTo(vP2[0], vP2[1]);
      ctx.strokeStyle = "rgba(14, 165, 233, 0.85)";
      ctx.lineWidth = 2.5;
      ctx.setLineDash([5, 4]);
      ctx.stroke();
      ctx.setLineDash([]);
    }
  }, [design, rotationAngle, pitchAngle]);

  return (
    <div className={`relative flex flex-col items-center justify-center rounded-[8px] border border-[var(--line)] bg-[var(--surface)] p-4 shadow-sm ${className}`}>
      {/* Header Bar with Illustrative Badge */}
      <div className="w-full flex items-center justify-between pb-2 mb-1 border-b border-[var(--line)] text-xs">
        <div className="flex items-center space-x-2">
          <Badge variant="neutral">Illustrative 3D model</Badge>
          <span className="text-[11px] text-[var(--ink-2)] hidden sm:inline">
            Responsive preview · Not to engineering scale
          </span>
        </div>

        {/* View Reset Control */}
        <button
          onClick={resetView}
          className="p-1 rounded-[6px] bg-[var(--surface-2)] border border-[var(--line)] text-[var(--ink)] hover:bg-[var(--surface)] transition flex items-center space-x-1"
          title="Reset 3D camera angle"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span className="text-[11px]">Reset view</span>
        </button>
      </div>

      {/* 3D Canvas */}
      <div className="relative w-full">
        <canvas
          ref={canvasRef}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          className="w-full h-64 sm:h-72 cursor-grab active:cursor-grabbing rounded-[6px]"
          title="Click and drag to rotate 3D shelter view"
        />

        {/* Floating Rotating Compass Indicator */}
        <div className="absolute top-3 left-3 flex items-center space-x-1.5 px-2 py-1 rounded-[6px] bg-[var(--surface)]/90 backdrop-blur-sm border border-[var(--line)] text-xs tabular-nums text-[var(--ink)] shadow-sm">
          <div
            className="w-4 h-4 flex items-center justify-center transition-transform duration-100"
            style={{ transform: `rotate(${design.orientation}deg)` }}
          >
            <Compass className="w-4 h-4 text-[var(--primary)]" />
          </div>
          <span className="font-medium">{design.orientation}° Azimuth</span>
        </div>
      </div>

      {/* Interactive Labels & Responsive Parameter Readouts */}
      {showLabels && (
        <div className="w-full mt-3 grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
          <div className="p-2 rounded-[6px] bg-[var(--surface-2)] border border-[var(--line)]">
            <span className="text-[var(--ink-2)] block text-[11px]">Roof thickness</span>
            <span className="font-semibold text-[var(--ink)] tabular-nums">
              {design.roof_insulation_thickness} mm insul.
            </span>
          </div>
          <div className="p-2 rounded-[6px] bg-[var(--surface-2)] border border-[var(--line)]">
            <span className="text-[var(--ink-2)] block text-[11px]">Wall reveal</span>
            <span className="font-semibold text-[var(--ink)] tabular-nums">
              {design.wall_insulation_thickness} mm ({design.wall_mass_class})
            </span>
          </div>
          <div className="p-2 rounded-[6px] bg-[var(--surface-2)] border border-[var(--line)]">
            <span className="text-[var(--ink-2)] block text-[11px]">Glazing & Overhang</span>
            <span className="font-semibold text-[var(--ink)] tabular-nums">
              {design.wwr}% WWR · {design.shading_depth.toFixed(2)}m
            </span>
          </div>
          <div className="p-2 rounded-[6px] bg-[var(--surface-2)] border border-[var(--line)]">
            <span className="text-[var(--ink-2)] block text-[11px]">Roof Finish</span>
            <span className="font-semibold text-[var(--ink)] tabular-nums">
              α = {design.roof_solar_absorptance.toFixed(2)} ({design.roof_solar_absorptance <= 0.4 ? "Cool" : "Dark"})
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

export default Shelter3DViewer;
