def penjumlahan(a,b):
    print(f"{a} + {b} = {a+b}")
    
def pengurangan(a,b):
    print(f"{a} - {b} = {a-b}")
    
def pembagian(a,b):
    print(f"{a} // {b} = {a//b}")
    
def perkalian(a,b):
    print(f"{a} * {b} = {a*b}")


status = True


while status:
    print("kalkulator")
    print()
    print("pilih opsi")
    print()
    print("1. penjumlahan")
    print("2. pengurangan")
    print("3. pembagian")
    print("4. perkalian")
    print("5. keluar")

    opsi = (input("pilih opsi"))

    if opsi == "5":
        print("anda keluar")
        status = False

    elif opsi in ("1","2","3","4"):

        numb1 = int(input("angka pertama: "))
        numb2 = int(input("angka kedua : "))

        if opsi == "1":
            print("====================================")
            print("hasil: ", numb1 + numb2)
            print("====================================")
        elif opsi == "2":
            print("====================================")
            print("hasil: ", numb1 - numb2)
            print("====================================")
        elif opsi == "3":
            print("====================================")
            print("hasil: ", numb1 // numb2)
            print("====================================")
        elif opsi == "4":
            print("====================================")
            print("hasil: ", numb1 * numb2)
            print("====================================")

