def distance_from_zero(n):
    if type(n) == int or type(n) == float:
        return abs(n)

    else:
        return "Nope"


original = raw_input("input a number:")
try:
    n = int(original)
    print(n)
    n = distance_from_zero(n)
    print(n)
except:
    print("input a number idiot")


    #x = x ^ 2
    #return(x)

    #return(x^2)




#print abs(n)