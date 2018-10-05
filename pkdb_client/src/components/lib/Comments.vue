<template>
    <div id="comments">
        <span v-for="item in comments" :key="item.pk">
            <UserAvatar :user="comment.user"></UserAvatar>
            {{ comment.text }}<br />
        </span>
    </div>
</template>

<script>
    export default {
        name: "Comments",
        props: {
            comments: {
                type: Object,
            }
        }
    }
</script>

<style scoped>

</style>