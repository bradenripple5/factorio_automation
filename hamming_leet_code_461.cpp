class Solution {
public:
    int hammingDistance(int x, int y) {

        //find out which integer has more digits and add to
        //differentDigitscount the number of ones;
        // this can be done with the getBinaryLength function
        if (getBinaryLength(x) > getBinaryLength(y)){
            return getNumberOfDifferentDigits(x,y);
        } 
        else { return getNumberOfDifferentDigits(y,x);}
 
    }
    // this assumes that the distance from 0 to x is greater than from y to 0, i.e. abs(x) > abs(y)
    int getNumberOfDifferentDigits(int x, int y){
        int differentDigitsCount = 0;
        int binLengthY = getBinaryLength(y);
        int binLengthX = getBinaryLength(x);
        int* binaryX = getBinary(x);
        int* binaryY = getBinary(y);
        // now take the lesser of the two, in this case y;
        for (int i = 0 ; i <binLengthY ; i++){
            if (binaryX[i]!=binaryY[i]) { differentDigitsCount++;}
        }
        for (int i = binLengthY; i < binLengthX; i++){
            if (binaryX[i]==1) { differentDigitsCount++;}
        }
        return differentDigitsCount;
}

    // next step is to chop the larger number down using getBinary
            // starting from the top down and then comparing 
    int* getBinary(int x){
        int* binaryNumbers;
        int digitPlace = 0;
        while (x!=0){
            std::cout << x;
            binaryNumbers[digitPlace] = x%2;
            x = x/2;
            digitPlace++;
        }
        return getBinary(x);
    }
    int getBinaryLength(int x){
        if (x <2 || x > -2){ return 1;}
        else {
            return 1+getBinaryLength(x/2);
        }
    }
};

int main()
{
    const Date d{ 2015, 10, 14 };
    d.print();

    return 0;
}
