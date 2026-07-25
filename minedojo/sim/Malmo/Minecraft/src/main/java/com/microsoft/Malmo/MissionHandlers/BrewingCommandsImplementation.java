// --------------------------------------------------------------------------------------------------
//  Copyright (c) 2016 Microsoft Corporation
//  
//  Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
//  associated documentation files (the "Software"), to deal in the Software without restriction,
//  including without limitation the rights to use, copy, modify, merge, publish, distribute,
//  sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
//  furnished to do so, subject to the following conditions:
//  
//  The above copyright notice and this permission notice shall be included in all copies or
//  substantial portions of the Software.
//  
//  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
//  NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
//  NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
//  DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
//  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
// --------------------------------------------------------------------------------------------------

package com.microsoft.Malmo.MissionHandlers;

import io.netty.buffer.ByteBuf;

import net.minecraft.entity.player.EntityPlayerMP;
import net.minecraft.inventory.ContainerBrewingStand;
import net.minecraft.inventory.Slot;
import net.minecraft.item.ItemStack;
import net.minecraftforge.fml.common.network.ByteBufUtils;
import net.minecraftforge.fml.common.network.simpleimpl.IMessage;
import net.minecraftforge.fml.common.network.simpleimpl.IMessageHandler;
import net.minecraftforge.fml.common.network.simpleimpl.MessageContext;

import com.microsoft.Malmo.MalmoMod;
import com.microsoft.Malmo.Schemas.MissionInit;

/**
 * Brewing commands allow agents to interact with brewing stands.
 * Commands: "brew" to open brewing stand GUI, "brewIngredient <slot>" to add ingredient to slot 0-2.
 */
public class BrewingCommandsImplementation extends CommandBase
{
    private boolean isOverriding;

    public static class BrewingMessage implements IMessage
    {
        String verb;
        String parameter;
        public BrewingMessage()
        {
        }
    
        public BrewingMessage(String verb, String parameter)
        {
            this.verb = verb;
            this.parameter = parameter;
        }

        @Override
        public void fromBytes(ByteBuf buf)
        {
            this.verb = ByteBufUtils.readUTF8String(buf);
            this.parameter = ByteBufUtils.readUTF8String(buf);
        }

        @Override
        public void toBytes(ByteBuf buf)
        {
            ByteBufUtils.writeUTF8String(buf, this.verb);
            ByteBufUtils.writeUTF8String(buf, this.parameter);
        }
    }

    public static class BrewingMessageHandler implements IMessageHandler<BrewingMessage, IMessage>
    {
        @Override
        public IMessage onMessage(final BrewingMessage message, MessageContext ctx)
        {
            final EntityPlayerMP player = ctx.getServerHandler().playerEntity;
            if (player == null)
                return null;

            player.getServer().addScheduledTask(new Runnable()
            {
                @Override
                public void run()
                {
                    if (message.verb.equalsIgnoreCase("brew"))
                    {
                        // Enable GUI interact for brewing stand
                        MalmoMod.setAllowGuiInteract(true);
                    }
                    else if (message.verb.equalsIgnoreCase("brewIngredient"))
                    {
                        if (player.openContainer instanceof ContainerBrewingStand)
                        {
                            ContainerBrewingStand container = (ContainerBrewingStand) player.openContainer;
                            // Move item from player's currently held slot to brewing ingredient slot
                            ItemStack held = player.inventory.getCurrentItem();
                            if (held != null)
                            {
                                // ContainerBrewingStand slot 0 is the ingredient slot
                                int ingredientSlot = 0;
                                ItemStack existing = container.getSlot(ingredientSlot).getStack();
                                if (existing == null || existing.isEmpty())
                                {
                                    container.getSlot(ingredientSlot).putStack(held.copy());
                                    player.inventory.setInventorySlotContents(
                                        player.inventory.currentItem, ItemStack.EMPTY);
                                    container.detectAndSendChanges();
                                }
                                else
                                {
                                    System.out.println("BrewingCommands: ingredient slot is not empty");
                                }
                            }
                            else
                            {
                                System.out.println("BrewingCommands: no item in hand to add");
                            }
                        }
                        else
                        {
                            System.out.println("BrewingCommands: no brewing stand GUI open");
                        }
                    }
                }
            });
            return null;
        }
    }

    @Override
    protected boolean onExecute(String verb, String parameter, MissionInit missionInit)
    {
        if (verb.equalsIgnoreCase("brew") || verb.equalsIgnoreCase("brewIngredient"))
        {
            MalmoMod.network.sendToServer(new BrewingMessage(verb, parameter));
            return true;
        }
        return false;
    }

    @Override
    public boolean parseParameters(Object params)
    {
        return true;
    }

    @Override
    public void install(MissionInit missionInit)
    {
    }

    @Override
    public void deinstall(MissionInit missionInit)
    {
    }

    @Override
    public boolean isOverriding()
    {
        return this.isOverriding;
    }

    @Override
    public void setOverriding(boolean b)
    {
        this.isOverriding = b;
    }
}
