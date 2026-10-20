import heapq

_NONE = object()


def merge_sorted(*iterables, key=None):
    its = [iter(x) for x in iterables]
    heap = []
    for i, it in enumerate(its):
        for item in it:
            heap.append((item if key is None else key(item), i, item))
            break
    heapq.heapify(heap)
    while heap:
        _k, i, item = heap[0]
        yield item
        nxt = _NONE
        for x in its[i]:
            nxt = x
            break
        if nxt is _NONE:
            heapq.heappop(heap)
        else:
            heapq.heapreplace(heap, (nxt if key is None else key(nxt), i, nxt))
