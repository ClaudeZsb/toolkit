package main

import (
	"encoding/csv"
	"log"
	"os"
	"sort"
	"strconv"
	"time"
)

func main() {
	if len(os.Args) < 3 {
		log.Fatalf("Usage: %s <part1.csv> <part2.csv> [output.csv]", os.Args[0])
	}

	part1File := os.Args[1]
	part2File := os.Args[2]
	outputFile := "aggregated.csv"
	if len(os.Args) >= 4 {
		outputFile = os.Args[3]
	}

	// Map to store daily aggregates: date -> {txCount, gasUsed}
	dailyStats := make(map[string]struct {
		TxCount int64
		GasUsed int64
	})

	// Process part1.csv
	if err := processCSV(part1File, dailyStats); err != nil {
		log.Fatalf("Error processing %s: %v", part1File, err)
	}

	// Process part2.csv
	if err := processCSV(part2File, dailyStats); err != nil {
		log.Fatalf("Error processing %s: %v", part2File, err)
	}

	// Sort dates
	dates := make([]string, 0, len(dailyStats))
	for date := range dailyStats {
		dates = append(dates, date)
	}
	sort.Strings(dates)

	// Create output CSV file
	outFile, err := os.Create(outputFile)
	if err != nil {
		log.Fatalf("Error creating output file %s: %v", outputFile, err)
	}
	defer outFile.Close()

	writer := csv.NewWriter(outFile)
	defer writer.Flush()

	// Write header
	if err := writer.Write([]string{"Date", "Tx Count", "Gas Consumed"}); err != nil {
		log.Fatalf("Error writing header: %v", err)
	}

	// Write results sorted by date
	for _, date := range dates {
		stats := dailyStats[date]
		record := []string{
			date,
			strconv.FormatInt(stats.TxCount, 10),
			strconv.FormatInt(stats.GasUsed, 10),
		}
		if err := writer.Write(record); err != nil {
			log.Fatalf("Error writing record: %v", err)
		}
	}

	log.Printf("Aggregation complete. Results written to %s", outputFile)
}

func processCSV(filename string, dailyStats map[string]struct {
	TxCount int64
	GasUsed int64
}) error {
	file, err := os.Open(filename)
	if err != nil {
		return err
	}
	defer file.Close()

	reader := csv.NewReader(file)
	records, err := reader.ReadAll()
	if err != nil {
		return err
	}

	// Skip header row
	for i := 1; i < len(records); i++ {
		record := records[i]
		if len(record) < 4 {
			continue
		}

		// Parse timestamp
		timestamp, err := strconv.ParseInt(record[1], 10, 64)
		if err != nil {
			log.Printf("Warning: Invalid timestamp in row %d: %v", i, err)
			continue
		}

		// Convert timestamp to date string (YYYY-MM-DD) in UTC
		t := time.Unix(timestamp, 0).UTC()
		date := t.Format("2006-01-02")

		// Parse transaction count
		txCount, err := strconv.ParseInt(record[2], 10, 64)
		if err != nil {
			log.Printf("Warning: Invalid tx count in row %d: %v", i, err)
			continue
		}

		// Parse gas used
		gasUsed, err := strconv.ParseInt(record[3], 10, 64)
		if err != nil {
			log.Printf("Warning: Invalid gas used in row %d: %v", i, err)
			continue
		}

		// Aggregate by date
		stats := dailyStats[date]
		stats.TxCount += txCount
		stats.GasUsed += gasUsed
		dailyStats[date] = stats
	}

	return nil
}
