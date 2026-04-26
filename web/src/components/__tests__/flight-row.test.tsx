import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { FlightRow } from "../flight-row";
import type { FlightRow as FlightRowType } from "@/lib/api-client";

const sample: FlightRowType = {
  route: "BKK-DAD",
  date: "2026-05-29",
  scrapedAt: "2026-04-26 13:08:50",
  airline: "Thai AirAsia",
  departureTime: "07:50",
  arrivalTime: "09:30",
  durationMinutes: 100,
  priceThb: 3621,
  bestBookingPrice: 3466,
  bestBookingSource: "Jettzy",
  isDirect: true,
};

describe("FlightRow", () => {
  it("shows the cheaper booking price when present", () => {
    render(<FlightRow flight={sample} />);
    expect(screen.getByText(/3,466/)).toBeInTheDocument();
    expect(screen.getByText(/Jettzy/)).toBeInTheDocument();
  });
  it("shows airline price when no booking source", () => {
    render(<FlightRow flight={{ ...sample, bestBookingPrice: null, bestBookingSource: null }} />);
    expect(screen.getByText(/3,621/)).toBeInTheDocument();
  });
  it("renders Direct badge for direct flights", () => {
    render(<FlightRow flight={sample} />);
    expect(screen.getByText("Direct")).toBeInTheDocument();
  });
});
