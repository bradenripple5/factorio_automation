from typing import List
import copy
class Solution:
    def get_rid_of_numbers_of_even_amounts(self,nums):
        nums = sorted(nums)
        nums_copy = copy.deepcopy(nums)
        for i in nums:
            if nums.count(i)>1 and nums.count(i)%2 == 0:
                while i in nums_copy:
                    nums_copy.remove(i)
                return nums_copy
        return nums_copy
    def make_number_count_dict(self,nums):
        numberdict = {}
        for i in nums:
            if i in numberdict:
                numberdict[i] += 1
            else:
                numberdict[i] = 1
        return numberdict
    def canPartition(self, nums: List[int]) -> bool:
        
        total_sum = sum(nums)
        
        return self.isSubsetSum(0,nums,total_sum//2)   
    def isSubsetSum (self, N, arr, summ):
        f = copy.deepcopy(summ)
        arr = sorted(arr[:])
        def subs(arr,summ,N=0):
            print(N)
            if arr and summ > 0:
                if arr[0] == summ:
                    return True
                if arr[0] < summ:
                    s = subs(arr[1:],summ-arr[0])
                    if s:
                        return True
                    else:
                        return subs(arr[1:],summ,N+1)
                return False
        
        
        if sum(arr) < summ:
            return False
        for i in arr:
            if i > summ:
                arr.remove(i)
            if i == summ:
                return True
        if sum(arr) * 2 < summ:
            summ = abs(summ - sum(arr))
        
                
        if subs(arr,summ):
            # print(subs(arr,summ))
            return True
        return False
        # code here 

if __name__ == "__main__":
    testcase = [100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,99,97]
    s = Solution()
    print(testcase.count(100), s.canPartition(testcase))
    print(s.make_number_count_dict(testcase))