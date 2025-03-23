test("Basic math test", () => {
    expect(2 + 2).toBe(4);
  });

  test("String comparison", () => {
    expect("Hello").toBe("Hello");
  });

  test("Array contains element", () => {
    const numbers = [1, 2, 3, 4, 5];
    expect(numbers).toContain(3);
  });
