describe("Basic math operations", () => {
    it("should correctly add numbers", () => {
      expect(3 + 3).toBe(6);
    });

    it("should correctly multiply numbers", () => {
      expect(4 * 2).toBe(8);
    });

    it("should correctly divide numbers", () => {
      expect(10 / 2).toBe(5);
    });

    it("should correctly subtract numbers", () => {
      expect(9 - 4).toBe(5);
    });
  });

  describe("String operations", () => {
    it("should match string values", () => {
      expect("Jest").toBe("Jest");
    });

    it("should verify string length", () => {
      expect("Testing".length).toBe(7);
    });
  });
