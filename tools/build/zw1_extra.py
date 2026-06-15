# The 45 characters still missing from 暨南《中文》第一册 (HANDOFF §6),
# by the lesson they belong to in ZW1.
ZW1_ADD = {
 3:  list("出入座立"),
 4:  list("地父母"),
 5:  list("电禾金"),
 6:  list("衣车瓜"),
 7:  list("生叫岁喜欢习"),
 8:  list("的"),
 9:  list("开真兴见老师们"),
 10: list("方向面太阳个"),
 11: list("季知唱叶"),
 12: list("新到闹穿戴帽祝体"),
}
if __name__=="__main__":
    allc=[c for v in ZW1_ADD.values() for c in v]
    print("total add:",len(allc))
